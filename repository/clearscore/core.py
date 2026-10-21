"""Deterministic, local PDF image cleanup. No OCR or generated music content.

The source image is already flattened, so original foreground alpha cannot be
recovered exactly. The guaranteed invariant is narrower: pixels below the
cutoff, colorful pixels, and detected staff rows retain their exact RGB values.
All other PDF objects remain in the cloned document.
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject
from .i18n import Message, tr


class CleanupError(Exception):
    """An error that can be explained directly in the desktop UI."""

    def __init__(self, key: str, **values):
        self.message = Message(key, values)
        super().__init__(tr(self.message))


class Cancelled(CleanupError):
    pass


@dataclass(frozen=True)
class Settings:
    # None = automatic threshold per image. Lower values remove darker grays.
    threshold: int | None = None
    protect_staff: bool = True
    color_tolerance: int = 16

    def __post_init__(self):
        if self.threshold is not None and not 170 <= self.threshold <= 240:
            raise ValueError("灰度阈值必须介于 170 与 240。")
        if not 0 <= self.color_tolerance <= 32:
            raise ValueError("颜色容差必须介于 0 与 32。")


@dataclass
class ImageReport:
    pages: list[int]
    width: int
    height: int
    detected: bool
    threshold: int | None
    background_peak: int | None
    changed_pixels: int = 0
    protected_dark_pixels: int = 0
    protected_staff_rows: int = 0
    protected_pixels_unchanged: bool = True
    reason: str | Message = ""


@dataclass
class Report:
    source_name: str
    source_sha256: str
    page_count: int
    settings: dict
    images: list[ImageReport] = field(default_factory=list)
    warnings: list[Message] = field(default_factory=list)
    page_boxes: list[dict] = field(default_factory=list)

    @property
    def processed_pages(self) -> list[int]:
        return sorted({p for image in self.images if image.changed_pixels for p in image.pages})

    @property
    def changed_pixels(self) -> int:
        # Shared PDF images count once; page associations are separately recorded.
        return sum(i.changed_pixels for i in self.images)

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "processed_pages": self.processed_pages,
            "changed_pixels": self.changed_pixels,
            "method": "neutral-gray threshold with dark-pixel and staff-row protection",
            "limitation": "Flattened scans cannot be restored pixel-for-pixel. "
            "Pale notation at or above the threshold can be affected; review the preview.",
        }


@dataclass
class PreparedPDF:
    source_bytes: bytes
    cleaned_bytes: bytes
    report: Report


def _profile(rgb: np.ndarray, tolerance: int) -> tuple[int | None, Message]:
    """Find a prominent pale neutral-gray mode, excluding white paper.

    Restrict automatic mode to predominantly monochrome, paper-like imagery.
    No claim is made to recognize a person, logo, or music semantics.
    """
    step = max(1, int(np.ceil(max(rgb.shape[:2]) / 1600)))
    sample = rgb[::step, ::step]
    lo = sample.min(axis=2)
    hi = sample.max(axis=2)
    neutral = hi.astype(np.int16) - lo <= tolerance
    if float(neutral.mean()) < 0.97:
        return None, Message("color_skip")
    if float((lo >= 247).mean()) < 0.35:
        return None, Message("color_skip")
    hist = np.bincount(lo[neutral].ravel(), minlength=256).astype(np.float64)
    smooth = np.convolve(hist, np.ones(5), mode="same")
    peak = 190 + int(np.argmax(smooth[190:243]))
    # Prefer the exact modal value within the smoothed peak neighborhood.
    start, end = max(190, peak - 2), min(244, peak + 3)
    peak = start + int(np.argmax(hist[start:end]))
    mass = float(hist[max(0, peak - 4):peak + 5].sum()) / lo.size
    if mass < 0.012:
        return None, Message("no_gray")
    if float((lo < 150).mean()) < 0.001:
        return None, Message("no_gray")
    return peak, Message("detected")


def clean_image(image: Image.Image, settings: Settings = Settings()) -> tuple[Image.Image, ImageReport]:
    if image.width * image.height > 60_000_000:
        raise CleanupError("image_large")
    if image.mode not in ("L", "RGB", "1"):
        raise CleanupError("unsupported_color", mode=image.mode)
    rgb = np.asarray(image.convert("RGB"))
    peak, reason = _profile(rgb, settings.color_tolerance)
    threshold = settings.threshold
    if threshold is None and peak is not None:
        threshold = int(np.clip(peak - 24, 180, 225))
    info = ImageReport([], image.width, image.height, peak is not None, threshold, peak, reason=reason)
    if threshold is None:
        return image.convert("RGB"), info

    lo = rgb.min(axis=2)
    hi = rgb.max(axis=2)
    dark = lo < threshold
    neutral = hi.astype(np.int16) - lo <= settings.color_tolerance
    remove = ~dark & neutral

    # Keep full spans of long horizontal rules. This prevents lifting faint
    # antialias pixels inside detected staff lines, including JPEG variations.
    if settings.protect_staff:
        rows = np.flatnonzero(np.count_nonzero(dark, axis=1) >= image.width * 0.42)
        for y in rows:
            xs = np.flatnonzero(dark[y])
            remove[y, xs[0]:xs[-1] + 1] = False
        info.protected_staff_rows = len(rows)

    out = rgb.copy()
    out[remove] = 255
    changed = np.any(out != rgb, axis=2)
    info.changed_pixels = int(changed.sum())
    info.protected_dark_pixels = int(dark.sum())
    info.protected_pixels_unchanged = bool(np.array_equal(out[~remove], rgb[~remove]))
    if not info.protected_pixels_unchanged:
        raise CleanupError("verification_failed")
    if peak is None:
        info.reason = Message("manual")
    return Image.fromarray(out), info


def _replace_image_stream(obj, image: Image.Image) -> None:
    """Replace only image samples, using lossless Flate rather than JPEG."""
    for key in ("/DecodeParms", "/Decode", "/Length", "/SMaskInData"):
        # Retain placement-independent metadata, interpolation, optional-content
        # membership and rendering intent. Only encoding-related keys change.
        obj.pop(NameObject(key), None)
    obj.update({
        NameObject("/Type"): NameObject("/XObject"),
        NameObject("/Subtype"): NameObject("/Image"),
        NameObject("/Width"): NumberObject(image.width),
        NameObject("/Height"): NumberObject(image.height),
        NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
        NameObject("/BitsPerComponent"): NumberObject(8),
        NameObject("/Filter"): NameObject("/FlateDecode"),
    })
    # pypdf EncodedStreamObject.set_data only supports an existing Flate stream;
    # assigning the encoded payload also handles prior DCT/JPX stream types.
    obj._data = zlib.compress(image.tobytes(), level=6)
    if hasattr(obj, "decoded_self"):
        obj.decoded_self = None


def prepare_pdf(
    source: str | Path,
    settings: Settings = Settings(),
    progress: Callable[[int, Message], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    password: str | None = None,
) -> PreparedPDF:
    path = Path(source)
    if not path.is_file():
        raise CleanupError("missing_file")
    if path.stat().st_size > 300_000_000:
        raise CleanupError("file_large")
    data = path.read_bytes()

    def check():
        if cancelled and cancelled():
            raise Cancelled("cancelled")

    def update(percent: int, message: Message):
        check()
        if progress:
            progress(percent, message)

    writer = None
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            if not reader.decrypt(password or ""):
                raise CleanupError("encrypted")
        if not reader.pages:
            raise CleanupError("empty_pdf")
        if len(reader.pages) > 300:
            raise CleanupError("too_many")
        report = Report(path.name, hashlib.sha256(data).hexdigest(), len(reader.pages), asdict(settings))
        if reader.is_encrypted:
            report.warnings.append(Message("unencrypted_output"))
        if reader.get_fields():
            raise CleanupError("forms")
        writer = PdfWriter(clone_from=reader)
        # Work on each referenced image once, even if it is shared by pages.
        objects: dict[tuple[int, int], dict] = {}
        for number, page in enumerate(writer.pages, 1):
            update(int(number / len(writer.pages) * 20), Message("analyze_progress", {"n": number, "count": len(writer.pages)}))
            report.page_boxes.append({
                "media": list(map(float, page.mediabox)),
                "crop": list(map(float, page.cropbox)),
                "rotation": page.rotation,
            })
            try:
                for image_file in page.images:
                    ref = image_file.indirect_reference
                    if ref is None:  # Do not rewrite inline images or content streams.
                        continue
                    obj = ref.get_object()
                    width, height = int(obj.get("/Width", 0)), int(obj.get("/Height", 0))
                    if width * height < 250_000:
                        continue
                    if width * height > 60_000_000:
                        raise CleanupError("image_large")
                    if any(k in obj for k in ("/SMask", "/Mask", "/ImageMask", "/Alternates")):
                        report.warnings.append(Message("mask_skip"))
                        continue
                    key = (ref.idnum, ref.generation)
                    if key in objects:
                        if number not in objects[key]["pages"]:
                            objects[key]["pages"].append(number)
                    else:
                        objects[key] = {"ref": ref, "file": image_file, "pages": [number]}
            except CleanupError:
                raise
            except Exception as exc:
                raise CleanupError("process_failed") from exc
        for index, entry in enumerate(objects.values()):
            update(20 + int(index / max(1, len(objects)) * 65), Message("clean_progress", {"n": index + 1, "count": len(objects)}))
            image = entry["file"].image
            if image.mode not in ("RGB", "L", "1"):
                report.warnings.append(Message("unsupported_color", {"mode": image.mode}))
                continue
            cleaned, info = clean_image(image, settings)
            info.pages = entry["pages"]
            report.images.append(info)
            if info.changed_pixels:
                _replace_image_stream(entry["ref"].get_object(), cleaned)
        update(88, Message("verify_progress"))
        output = io.BytesIO()
        writer.write(output)
        result = output.getvalue()
        verify = PdfReader(io.BytesIO(result))
        if len(verify.pages) != len(reader.pages):
            raise CleanupError("verification_failed")
        for i, (before, after) in enumerate(zip(reader.pages, verify.pages)):
            if (list(before.mediabox) != list(after.mediabox)
                    or list(before.cropbox) != list(after.cropbox)
                    or before.rotation != after.rotation):
                raise CleanupError("verification_failed")
            # Score layout/placement operators are preserved byte-for-byte.
            before_content, after_content = before.get_contents(), after.get_contents()
            if ((before_content.get_data() if before_content else b"")
                    != (after_content.get_data() if after_content else b"")):
                raise CleanupError("verification_failed")
        if len(report.processed_pages) != report.page_count:
            untouched = sorted(set(range(1, report.page_count + 1)) - set(report.processed_pages))
            report.warnings.append(Message("some_unchanged"))
        update(100, Message("complete"))
        return PreparedPDF(data, result, report)
    except (CleanupError, Cancelled):
        raise
    except Exception as exc:
        raise CleanupError("process_failed") from exc
    finally:
        if writer:
            writer.close()


def save_pdf(prepared: PreparedPDF, destination: str | Path, source: str | Path) -> Path:
    """Atomic output. The input may never be overwritten, including hardlinks."""
    target, origin = Path(destination), Path(source)
    if target.suffix.lower() != ".pdf":
        target = target.with_suffix(".pdf")
    if target.resolve() == origin.resolve() or (
        target.exists() and origin.exists() and os.path.samefile(target, origin)
    ):
        raise CleanupError("overwrite_source")
    if not target.parent.is_dir():
        raise CleanupError("missing_folder")
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".clearscore-", suffix=".tmp", delete=False) as stream:
            temp_name = stream.name
            stream.write(prepared.cleaned_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except OSError as exc:
        raise CleanupError("save_failed") from exc
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return target
