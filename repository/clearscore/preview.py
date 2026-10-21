"""PDFium is used only for display; rendered pages are never exported."""

import threading

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

_render_lock = threading.Lock()


def render_page(data: bytes, index: int, max_side: int = 1800) -> Image.Image:
    with _render_lock:
        with pdfium.PdfDocument(data) as document:
            page = document[index]
            try:
                scale = min(max_side / max(page.get_size()), 3.0)
                bitmap = page.render(scale=scale)
                try:
                    return bitmap.to_pil().convert("RGB").copy()
                finally:
                    bitmap.close()
            finally:
                page.close()


def difference_image(before: Image.Image, after: Image.Image) -> Image.Image:
    """A teal highlight shows modified displayed pixels, over a light original."""
    a, b = np.array(before), np.array(after)
    changed = np.any(a != b, axis=2)
    view = (a.astype(np.float32) * 0.22 + 255 * 0.78).astype(np.uint8)
    view[changed] = (64, 157, 127)
    return Image.fromarray(view)
