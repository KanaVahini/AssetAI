"""
Handles standalone image files (.png, .jpg, .jpeg, .tif, .tiff) —
e.g. a photographed inspection form or a scanned single-page document.
"""

from PIL import Image

from schema import make_doc_shell, make_page
from ocr_utils import ocr_image


def process_image(path) -> dict:
    img = Image.open(path)
    text, conf = ocr_image(img)

    doc = make_doc_shell(path, "image")
    doc["pages"] = [make_page(1, text, tables=[], ocr_confidence=conf, extra_meta={"extraction_method": "ocr", "source_type": "image"})]
    return doc
