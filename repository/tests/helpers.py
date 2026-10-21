import io
import zlib

from PIL import Image, ImageDraw
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject, EncodedStreamObject, DictionaryObject, NameObject, NumberObject,
)


def score_image(watermark=True):
    image = Image.new("RGB", (800, 1100), "white")
    draw = ImageDraw.Draw(image)
    if watermark:
        draw.ellipse((180, 160, 620, 920), fill=(229, 229, 229))
    for block in range(4):
        y = 160 + block * 220
        for line in range(6):
            draw.line((45, y + line * 13, 755, y + line * 13), fill=(145, 145, 145), width=1)
        for note in range(8):
            x = 90 + note * 84
            note_y = y + (note % 5) * 13
            draw.ellipse((x - 7, note_y - 4, x + 7, note_y + 5), fill="black")
            draw.line((x + 7, note_y, x + 7, note_y - 43), fill="black", width=2)
    return image


def make_pdf(path, image=None, pages=1, shared=False, rotated=False, vector=False):
    writer = PdfWriter()
    image = image or score_image()
    stream = EncodedStreamObject()
    stream.update({
        NameObject("/Type"): NameObject("/XObject"),
        NameObject("/Subtype"): NameObject("/Image"),
        NameObject("/Width"): NumberObject(image.width),
        NameObject("/Height"): NumberObject(image.height),
        NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
        NameObject("/BitsPerComponent"): NumberObject(8),
        NameObject("/Filter"): NameObject("/FlateDecode"),
        NameObject("/Interpolate"): __import__("pypdf").generic.BooleanObject(False),
    })
    stream._data = zlib.compress(image.tobytes())
    ref = writer._add_object(stream)
    for _ in range(pages):
        page = writer.add_blank_page(600, 825)
        content = DecodedStreamObject()
        operators = b"q 600 0 0 825 0 0 cm /Im0 Do Q\n"
        if vector:
            operators += b"0 0 1 RG 3 w 20 20 m 580 800 l S\n"
        content.set_data(operators)
        page[NameObject("/Contents")] = writer._add_object(content)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): ref})
        })
        if rotated:
            page.rotate(90)
            page.cropbox.lower_left = (10, 15)
    if shared:
        # All pages above deliberately share an image XObject.
        assert pages > 1
    writer.add_metadata({"/Title": "Synthetic score", "/Author": "Test author"})
    with open(path, "wb") as output:
        writer.write(output)
    return path
