"""Local adapters for images and Word. No document reflow or external service."""
from __future__ import annotations

import hashlib
import io
import os
import posixpath
import tempfile
import zipfile
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, ImageOps
from pi_heif import register_heif_opener
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject, DictionaryObject, EncodedStreamObject, NameObject, NumberObject,
)

from .core import CleanupError, Cancelled, Report, Settings, clean_image, prepare_pdf
from .i18n import Message
from .preview import render_page

register_heif_opener()
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".dib", ".webp", ".tif", ".tiff",
    ".gif", ".ico", ".avif", ".heic", ".heif", ".jp2", ".j2k", ".jpf", ".jpx",
    ".tga", ".ppm", ".pgm", ".pbm", ".pnm",
}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf", ".docx"}
MAX_TOTAL_PIXELS = 60_000_000


@dataclass
class Frame:
    original: Image.Image
    cleaned: Image.Image
    metadata: dict = field(default_factory=dict)
    name: str = ""


@dataclass
class Document:
    kind: str
    source_bytes: bytes
    cleaned_bytes: bytes
    report: Report
    frames: list[Frame] = field(default_factory=list)

    @property
    def default_suffix(self):
        return {"pdf": ".pdf", "docx": ".docx"}.get(
            self.kind, ".tiff" if len(self.frames) > 1 else ".png"
        )

    @property
    def item_key(self):
        if self.kind == "pdf":
            return "page_item"
        if self.kind == "docx" or len(self.frames) == 1:
            return "image_item"
        return "page_item" if Path(self.report.source_name).suffix.lower() in (".tif", ".tiff") else "frame_item"

    def preview(self, index):
        if self.kind == "pdf":
            return render_page(self.source_bytes, index), render_page(self.cleaned_bytes, index)
        frame = self.frames[index]
        result = []
        for image in (frame.original, frame.cleaned):
            # Previews are always rendered on paper; exported alpha is unchanged.
            if image.mode == "RGBA":
                paper = Image.new("RGBA", image.size, "white")
                paper.alpha_composite(image)
                image = paper.convert("RGB")
            else:
                image = image.convert("RGB")
            image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            result.append(image)
        return tuple(result)


def _check(cancelled):
    if cancelled and cancelled():
        raise Cancelled("cancelled")


def _notify(progress, cancelled, value, key, **values):
    _check(cancelled)
    if progress:
        progress(value, Message(key, values))


def _decode(data: bytes, report: Report, cancelled=None):
    frames = []
    with Image.open(io.BytesIO(data)) as source:
        count = getattr(source, "n_frames", 1)
        if count > 300:
            raise CleanupError("too_many")
        if getattr(source, "is_animated", False):
            report.warnings.append(Message("frames_note"))
        total = 0
        for index in range(count):
            _check(cancelled)
            source.seek(index)
            pixels = source.width * source.height
            if pixels > 60_000_000:
                raise CleanupError("image_large")
            total += pixels
            if total > MAX_TOTAL_PIXELS:
                raise CleanupError("memory_limit")
            metadata = {k: source.info[k] for k in ("dpi", "icc_profile") if k in source.info}
            # Normalize EXIF orientation once, and never copy a stale orientation tag.
            image = ImageOps.exif_transpose(source.copy())
            if image.mode in ("RGBA", "LA") or "transparency" in source.info:
                image = image.convert("RGBA")
            elif image.mode not in ("1", "L", "RGB"):
                if image.mode != "P":
                    report.warnings.append(Message("color_converted"))
                    # A source CMYK/16-bit profile must not be attached to RGB pixels.
                    metadata.pop("icc_profile", None)
                image = image.convert("RGB")
            frames.append((image, metadata))
    return frames


def _clean_frame(image, settings, number):
    alpha = image.getchannel("A") if image.mode == "RGBA" else None
    if alpha is not None:
        analysis_image = Image.new("RGBA", image.size, "white")
        analysis_image.alpha_composite(image)
        cleaned, info = clean_image(analysis_image.convert("RGB"), settings)
        # Partially transparent and invisible pixels are kept exactly as stored.
        original = np.array(image)
        out = original.copy()
        opaque = np.array(alpha) == 255
        out[opaque, :3] = np.array(cleaned)[opaque]
        info.changed_pixels = int(np.any(out != original, axis=2).sum())
        cleaned = Image.fromarray(out)
    else:
        cleaned, info = clean_image(image, settings)
        if image.mode in ("1", "L"):
            cleaned = cleaned.convert(image.mode)
    info.pages = [number]
    return cleaned, info


def _encode_image(frames, suffix):
    first = frames[0].cleaned
    metadata = frames[0].metadata
    output = io.BytesIO()
    if len(frames) > 1 and suffix not in (".tif", ".tiff", ".pdf"):
        raise CleanupError("multi_export")
    if suffix == ".pdf":
        return _image_pdf(frames)
    if suffix == ".png":
        first.save(output, "PNG", **metadata)
    elif suffix in (".tif", ".tiff"):
        first.save(output, "TIFF", save_all=True,
                   append_images=[f.cleaned for f in frames[1:]],
                   compression="tiff_deflate", **metadata)
    elif suffix in (".jpg", ".jpeg"):
        # JPEG cannot preserve exact pixels or transparency. UI asks explicitly.
        rgb = Image.new("RGB", first.size, "white")
        rgb.paste(first.convert("RGB"), mask=first.getchannel("A") if first.mode == "RGBA" else None)
        rgb.save(output, "JPEG", quality=98, subsampling=0, **metadata)
    elif suffix == ".webp":
        first.save(output, "WEBP", lossless=True, exact=True,
                   **{k: v for k, v in metadata.items() if k == "icc_profile"})
    else:
        raise CleanupError("bad_export")
    return output.getvalue()


def _image_pdf(frames):
    """Flate RGB samples with separate alpha mask, never Pillow's JPEG PDF path."""
    writer = PdfWriter()
    for frame in frames:
        image = frame.cleaned
        dpi = frame.metadata.get("dpi", (300, 300))
        try:
            dx, dy = (float(d) for d in dpi)
            if not 10 <= dx <= 9600 or not 10 <= dy <= 9600:
                dx = dy = 300
        except (ValueError, TypeError):
            dx = dy = 300
        width, height = image.width * 72 / dx, image.height * 72 / dy
        page = writer.add_blank_page(width, height)
        obj = EncodedStreamObject()
        obj.update({
            NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(image.width), NameObject("/Height"): NumberObject(image.height),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8),
            NameObject("/Filter"): NameObject("/FlateDecode"),
        })
        obj._data = zlib.compress(image.convert("RGB").tobytes())
        if image.mode == "RGBA":
            mask = EncodedStreamObject()
            mask.update({**obj, NameObject("/ColorSpace"): NameObject("/DeviceGray")})
            mask._data = zlib.compress(image.getchannel("A").tobytes())
            obj[NameObject("/SMask")] = writer._add_object(mask)
        image_ref = writer._add_object(obj)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/XObject"): DictionaryObject({NameObject("/Score"): image_ref})
        })
        content = DecodedStreamObject()
        content.set_data(f"q {width:.8f} 0 0 {height:.8f} 0 0 cm /Score Do Q".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)
    output = io.BytesIO()
    writer.write(output)
    writer.close()
    return output.getvalue()


def _prepare_docx(data, report, settings, progress, cancelled):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "word/document.xml" not in names:
            raise CleanupError("process_failed")
        if any(n.startswith("_xmlsignatures/") for n in names):
            raise CleanupError("signed_docx")
        if sum(i.file_size for i in archive.infolist()) > 512_000_000:
            raise CleanupError("file_large")
        # Read only in memory; no archive member is extracted to a filesystem path.
        parts = {name: archive.read(name) for name in names}
        media = [n for n in names if n.startswith("word/media/") and Path(n).suffix.lower() in IMAGE_EXTENSIONS]
        if not media:
            raise CleanupError("no_images")
        renamed, replacements, frames = {}, {}, []
        total = 0
        for index, name in enumerate(media):
            _notify(progress, cancelled, int(index / len(media) * 85), "clean_progress", n=index + 1, count=len(media))
            decoded = _decode(parts[name], report, cancelled)
            current = []
            for original, metadata in decoded:
                total += original.width * original.height
                if total > MAX_TOTAL_PIXELS:
                    raise CleanupError("memory_limit")
                if len(frames) >= 300:
                    raise CleanupError("too_many")
                cleaned, info = _clean_frame(original, settings, len(frames) + 1)
                report.images.append(info)
                frame = Frame(original, cleaned, metadata, name)
                frames.append(frame)
                current.append(frame)
            if any(i.changed_pixels for i in report.images[-len(current):]):
                extension = ".tiff" if len(current) > 1 else ".png"
                new_name = posixpath.splitext(name)[0] + "_clearscore" + extension
                while new_name in parts or new_name in replacements:
                    new_name = posixpath.splitext(new_name)[0] + "_" + extension
                renamed[name] = new_name
                replacements[new_name] = _encode_image(current, extension)
        if not frames:
            raise CleanupError("no_images")
        report.page_count = len(frames)
        report.warnings.append(Message("docx_preview"))
        # Rewrite only relationships that target changed media. Document text,
        # drawings, positions, styles, section properties and other XML stay intact.
        for name in names:
            if not name.endswith(".rels"):
                continue
            root = ET.fromstring(parts[name])
            base = posixpath.dirname(posixpath.dirname(name))
            changed = False
            for relationship in root:
                if relationship.get("TargetMode") == "External":
                    continue
                target = unquote(relationship.get("Target", ""))
                absolute = posixpath.normpath(posixpath.join(base, target)).lstrip("/")
                if absolute in renamed:
                    relationship.set("Target", quote(posixpath.relpath(renamed[absolute], base or "."), safe="/"))
                    changed = True
            if changed:
                replacements[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        if renamed:
            root = ET.fromstring(parts["[Content_Types].xml"])
            ns = "{http://schemas.openxmlformats.org/package/2006/content-types}"
            # Per-part overrides are precise and do not disturb other PNG/TIFF files.
            for node in list(root):
                if node.tag == ns + "Override" and node.get("PartName", "").lstrip("/") in renamed:
                    root.remove(node)
            for name in renamed.values():
                ET.SubElement(root, ns + "Override", {
                    "PartName": "/" + name,
                    "ContentType": "image/png" if name.endswith(".png") else "image/tiff",
                })
            replacements["[Content_Types].xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        _notify(progress, cancelled, 92, "verify_progress")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as result:
            for info in archive.infolist():
                if info.filename not in renamed:
                    result.writestr(info, replacements.pop(info.filename, parts[info.filename]))
            for name, value in replacements.items():
                result.writestr(name, value)
        result_data = output.getvalue()
        with zipfile.ZipFile(io.BytesIO(result_data)) as verify:
            for name in names:
                if name not in renamed and not name.endswith(".rels") and name != "[Content_Types].xml":
                    if verify.read(name) != parts[name]:
                        raise CleanupError("verification_failed")
        return Document("docx", data, result_data, report, frames)


def prepare_document(source, settings=Settings(), progress=None, cancelled=None):
    path = Path(source)
    if path.suffix.lower() == ".doc":
        raise CleanupError("legacy_word")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise CleanupError("unsupported")
    if not path.is_file():
        raise CleanupError("missing_file")
    if path.stat().st_size > 300_000_000:
        raise CleanupError("file_large")
    if path.suffix.lower() == ".pdf":
        prepared = prepare_pdf(path, settings, progress, cancelled)
        return Document("pdf", prepared.source_bytes, prepared.cleaned_bytes, prepared.report)
    _check(cancelled)
    data = path.read_bytes()
    report = Report(path.name, hashlib.sha256(data).hexdigest(), 0, asdict(settings))
    try:
        if path.suffix.lower() == ".docx":
            prepared = _prepare_docx(data, report, settings, progress, cancelled)
        else:
            decoded = _decode(data, report, cancelled)
            report.page_count = len(decoded)
            frames = []
            for index, (original, metadata) in enumerate(decoded):
                _notify(progress, cancelled, int(index / len(decoded) * 95), "clean_progress", n=index + 1, count=len(decoded))
                cleaned, info = _clean_frame(original, settings, index + 1)
                report.images.append(info)
                frames.append(Frame(original, cleaned, metadata))
            prepared = Document("image", data, b"", report, frames)
        if len(report.processed_pages) < report.page_count:
            report.warnings.append(Message("some_unchanged"))
        # Preserve order but avoid repeating the same warning for every image.
        report.warnings = list({(m.key, str(m.values)): m for m in report.warnings}.values())
        _notify(progress, cancelled, 100, "complete")
        return prepared
    except CleanupError:
        raise
    except Exception as exc:
        raise CleanupError("process_failed") from exc


def write_atomic(data, destination, source):
    target, origin = Path(destination), Path(source)
    if target.resolve() == origin.resolve() or (
        target.exists() and origin.exists() and os.path.samefile(target, origin)
    ):
        raise CleanupError("overwrite_source")
    if not target.parent.is_dir():
        raise CleanupError("missing_folder")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".clearscore-", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        raise CleanupError("save_failed") from exc
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return target


def save_document(prepared, destination, source):
    target = Path(destination)
    if not target.suffix:
        target = target.with_suffix(prepared.default_suffix)
    try:
        if prepared.kind in ("pdf", "docx"):
            if target.suffix.lower() != prepared.default_suffix:
                raise CleanupError("bad_export")
            data = prepared.cleaned_bytes
        else:
            data = _encode_image(prepared.frames, target.suffix.lower())
        return write_atomic(data, target, source)
    except CleanupError:
        raise
    except Exception as exc:
        raise CleanupError("save_failed") from exc
