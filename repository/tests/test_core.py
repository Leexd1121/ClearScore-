import hashlib
import io
import os

import numpy as np
import pytest
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter

from clearscore.core import Cancelled, CleanupError, Settings, clean_image, prepare_pdf, save_pdf
from tests.helpers import make_pdf, score_image


def test_auto_detects_watermark_and_preserves_dark_pixels():
    source = score_image()
    result, report = clean_image(source)
    a, b = np.array(source), np.array(result)
    assert report.background_peak == 229
    assert report.threshold == 205
    dark = a.min(axis=2) < report.threshold
    assert np.array_equal(a[dark], b[dark])
    assert np.all(b[400, 400] == 255)
    assert report.protected_pixels_unchanged
    assert report.changed_pixels > 100_000


def test_staff_guard_preserves_faint_segments():
    image = score_image()
    a = np.array(image)
    a[160, 200:500] = 220
    cleaned, report = clean_image(Image.fromarray(a))
    assert report.protected_staff_rows > 0
    assert np.array_equal(np.array(cleaned)[160, 200:500], a[160, 200:500])
    unprotected, _ = clean_image(Image.fromarray(a), Settings(protect_staff=False))
    assert np.all(np.array(unprotected)[160, 200:500] == 255)


def test_color_is_not_removed_even_in_manual_mode():
    image = score_image()
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 70, 70), fill=(225, 210, 250))
    result, _ = clean_image(image, Settings(190))
    assert result.getpixel((35, 35)) == image.getpixel((35, 35))


def test_white_score_is_not_changed_by_auto():
    image = score_image(watermark=False)
    result, report = clean_image(image)
    assert report.threshold is None
    assert report.changed_pixels == 0
    assert np.array_equal(np.array(image), np.array(result))


def test_photographic_background_is_not_auto_processed():
    rng = np.random.default_rng(42)
    image = Image.fromarray(rng.integers(30, 240, (600, 600, 3), dtype=np.uint8))
    result, report = clean_image(image)
    assert not report.detected
    assert report.changed_pixels == 0
    assert np.array_equal(np.array(image), np.array(result))


def test_pdf_export_is_lossless_and_preserves_layout(tmp_path):
    source = make_pdf(tmp_path / "source.pdf", pages=2, shared=True, rotated=True, vector=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    prepared = prepare_pdf(source)
    target = save_pdf(prepared, tmp_path / "clean.pdf", source)
    original, result = PdfReader(source), PdfReader(target)
    expected, _ = clean_image(original.pages[0].images[0].image)
    assert len(result.pages) == 2
    assert prepared.report.processed_pages == [1, 2]
    assert len(prepared.report.images) == 1
    for before, after in zip(original.pages, result.pages):
        assert before.get_contents().get_data() == after.get_contents().get_data()
        assert before.mediabox == after.mediabox
        assert before.cropbox == after.cropbox
        assert before.rotation == after.rotation == 90
        assert np.array_equal(np.array(after.images[0].image), np.array(expected))
        assert after.images[0].indirect_reference.get_object().get("/Interpolate") is not None
    assert result.metadata.title == original.metadata.title
    assert result.metadata.author == original.metadata.author
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest


def test_input_cannot_be_overwritten_or_hardlinked(tmp_path):
    source = make_pdf(tmp_path / "input.pdf")
    prepared = prepare_pdf(source)
    with pytest.raises(CleanupError, match="原始"):
        save_pdf(prepared, source, source)
    linked = tmp_path / "linked.pdf"
    os.link(source, linked)
    with pytest.raises(CleanupError, match="原始"):
        save_pdf(prepared, linked, source)


def test_unsupported_pages_are_reported(tmp_path):
    path = tmp_path / "vector.pdf"
    writer = PdfWriter()
    writer.add_blank_page(200, 300)
    writer.write(path)
    prepared = prepare_pdf(path)
    assert not prepared.report.changed_pixels
    assert prepared.report.warnings
    assert prepared.report.page_count == 1


def test_cancellation_does_not_write_any_output(tmp_path):
    source = make_pdf(tmp_path / "source.pdf")
    with pytest.raises(Cancelled):
        prepare_pdf(source, cancelled=lambda: True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["source.pdf"]


def test_broken_and_encrypted_files_explain_error(tmp_path):
    invalid = tmp_path / "broken.pdf"
    invalid.write_bytes(b"broken")
    with pytest.raises(CleanupError, match="无法处理"):
        prepare_pdf(invalid)
    writer = PdfWriter()
    writer.add_blank_page(200, 300)
    writer.encrypt("private-test-password")
    locked = tmp_path / "locked.pdf"
    writer.write(locked)
    with pytest.raises(CleanupError, match="加密"):
        prepare_pdf(locked)


def test_manual_threshold_validation():
    with pytest.raises(ValueError):
        Settings(100)
    with pytest.raises(ValueError):
        Settings(color_tolerance=99)


def test_source_fixture_regression_when_supplied():
    """Optional private sample; never add a copyrighted score to the repository."""
    path = os.environ.get("CLEARSCORE_SAMPLE_PDF")
    if not path:
        pytest.skip("No private PDF sample supplied")
    original = PdfReader(path)
    prepared = prepare_pdf(path)
    result = PdfReader(io.BytesIO(prepared.cleaned_bytes))
    assert len(result.pages) == len(original.pages)
    assert len(prepared.report.processed_pages) == len(original.pages)
    for before, after in zip(original.pages, result.pages):
        a, b = np.array(before.images[0].image), np.array(after.images[0].image)
        assert a.shape == b.shape
        dark = a.min(axis=2) < 205
        assert np.array_equal(a[dark], b[dark])
        expected, _ = clean_image(before.images[0].image)
        assert np.array_equal(b, np.array(expected))
        assert before.get_contents().get_data() == after.get_contents().get_data()
