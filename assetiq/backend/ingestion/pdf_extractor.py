"""
Handles .pdf files.

Strategy: try digital text extraction per page (fast, accurate). If a page
has almost no extractable text (common when a scanned image is embedded in
an otherwise-digital PDF — frequent in P&IDs and old inspection reports),
rasterize that specific page and OCR it instead. This is a per-PAGE decision,
not a per-FILE decision, because real industrial PDFs are often mixed.
"""

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

from schema import make_doc_shell, make_page
from ocr_utils import ocr_image

MIN_TEXT_CHARS_PER_PAGE = 20  # below this, treat page as scanned


def _extract_tables_for_page(plumber_page):
    try:
        return [{"rows": t} for t in plumber_page.extract_tables()]
    except Exception:
        return []


def _extract_sorted_text(fpage) -> str:
    try:
        return fpage.get_text("text", sort=True).strip()
    except Exception:
        return fpage.get_text().strip()


def _should_ocr_page(fpage, digital_text: str) -> bool:
    if len(digital_text) < MIN_TEXT_CHARS_PER_PAGE:
        return True

    try:
        words = fpage.get_text("words")
        blocks = fpage.get_text("blocks")
    except Exception:
        return False

    if len(words) < 10 and len(blocks) <= 2 and len(digital_text) < 80:
        return True

    alpha_ratio = sum(1 for char in digital_text if char.isalnum()) / max(len(digital_text), 1)
    return alpha_ratio < 0.25


def process_pdf(path) -> dict:
    fitz_doc = fitz.open(path)
    plumber_doc = pdfplumber.open(path)

    any_scanned = False
    pages_out = []

    for i, (fpage, ppage) in enumerate(zip(fitz_doc, plumber_doc.pages)):
        digital_text = _extract_sorted_text(fpage)
        tables = _extract_tables_for_page(ppage)

        if not _should_ocr_page(fpage, digital_text):
            pages_out.append(make_page(i + 1, digital_text, tables, ocr_confidence=None, extra_meta={"extraction_method": "digital_sorted", "source_type": "pdf"}))
        else:
            any_scanned = True
            pix = fpage.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text, conf = ocr_image(img)
            pages_out.append(make_page(i + 1, text, tables, ocr_confidence=conf, extra_meta={"extraction_method": "ocr_fallback", "source_type": "pdf"}))

    plumber_doc.close()
    fitz_doc.close()

    doc = make_doc_shell(path, "pdf_scanned" if any_scanned else "pdf_digital")
    doc["pages"] = pages_out
    return doc
