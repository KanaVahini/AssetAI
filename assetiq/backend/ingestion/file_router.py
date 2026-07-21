"""
file_router.py
--------------
Routes any file to the correct extractor based on file extension.
For PDFs, applies a 3-way smart routing:
  1. P&ID drawings      → pid_extractor (if available)
  2. Mixed docs         → mixed_doc_extractor (tables + figures + prose)
  3. Plain text PDFs    → pdf_extractor

Works for any plant — no hardcoded assumptions.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import fitz
from pdf_extractor import process_pdf
from csv_extractor import process_tabular
from ocr_extractor import process_image
from email_extractor import process_email
from mixed_doc_extractor import process_document as process_mixed_doc
from layout_classifier import classify_page_regions

# pid_extractor.py may not exist yet in every checkout. Import it
# defensively so the whole router doesn't crash on load if it's missing.
try:
    from pid_extractor import process_pid, is_pid_drawing
    _PID_AVAILABLE = True
except ImportError:
    _PID_AVAILABLE = False

    def is_pid_drawing(file_path):
        return False

    def process_pid(file_path):
        raise RuntimeError("pid_extractor.py is not available in this environment")


SUPPORTED_EXTENSIONS = [
    ".pdf", ".csv", ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png", ".tiff", ".bmp",
    ".txt", ".eml", ".msg",
]


def supported_extensions():
    """Used by pipeline.py to decide which files in a folder to pick up."""
    return SUPPORTED_EXTENSIONS


def route_pdf(file_path):
    """
    Three-way split for PDFs:
      1. Genuine P&ID / drawing                         → pid_extractor.process_pid
      2. Mixed report/paper (prose + tables + figures)  → mixed_doc_extractor.process_document
      3. Plain text-only document (SOP, memo, contract) → pdf_extractor.process_pdf

    Scans EVERY page — if ANY page has a table, diagram, or photo region,
    the whole document goes through mixed_doc_extractor which handles each
    region type independently. Only documents where no page has structured
    content fall back to plain pdf_extractor.
    """
    if _PID_AVAILABLE and is_pid_drawing(file_path):
        return process_pid(file_path)

    doc = fitz.open(file_path)
    page_count = doc.page_count
    doc.close()

    has_structured_content = False
    for page_index in range(page_count):
        try:
            layout = classify_page_regions(file_path, page_index=page_index)
            if layout["table_regions"] or layout["diagram_regions"] or layout["photo_regions"]:
                has_structured_content = True
                break
        except Exception:
            continue  # if layout classification fails on a page, skip it

    if has_structured_content:
        return process_mixed_doc(file_path)

    return process_pdf(file_path)


def route_file(file_path):
    """
    Routes any file to the correct extractor.
    Works for any file from any plant.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return route_pdf(file_path)

    elif ext in [".csv", ".xlsx", ".xls"]:
        return process_tabular(file_path)

    elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        return process_image(file_path)

    elif ext in [".txt", ".eml", ".msg"]:
        return process_email(file_path)

    else:
        print(f"  Unsupported file type: {ext}")
        return None


def get_handler(ext: str):
    """Used by pipeline.py: given a file extension, return the callable
    that should process it, or None if unsupported."""
    ext = ext.lower()
    if ext == ".pdf":
        return route_pdf
    elif ext in [".csv", ".xlsx", ".xls"]:
        return process_tabular
    elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        return process_image
    elif ext in [".txt", ".eml", ".msg"]:
        return process_email
    else:
        return None
