"""
pid_extractor.py
-----------------
P&ID (Piping and Instrumentation Diagram) extractor.
Extracts equipment tags, instrument tags, and text from P&ID drawings.

Strategy:
1. Detect if file is a P&ID using filename + content heuristics
2. For each page: try digital text extraction first
3. If insufficient text (scanned drawing) → fall back to OCR at high DPI
4. Extract all equipment/instrument tags using regex patterns
5. Return standard document format compatible with the rest of the pipeline

Works for:
- Digital P&ID PDFs (text layer present)
- Scanned P&ID PDFs (OCR fallback)
- P&ID images (JPEG, PNG, TIFF)

Dependencies: pymupdf, pytesseract (optional for OCR fallback)
"""

import os
import re
import sys
import fitz

sys.path.insert(0, os.path.dirname(__file__))
from schema import make_doc_shell, make_page

# ── Tag Patterns ──────────────────────────────────────────────
# Covers standard ISA/IEC P&ID tag formats used in Indian industry
TAG_PATTERNS = [
    # Standard instrument tags: FIC-101, LT-201A, PSHH-301
    r'\b[A-Z]{2,5}-\d{3,4}[A-Z]?\b',

    # Equipment tags: P-104, V-22, HX-11, BL-07
    r'\b[A-Z]{1,3}-\d{1,3}[A-Z]?\b',

    # Tags with unit suffix: P-104A, V-22B
    r'\b[A-Z]{1,4}-\d{1,4}[A-Z]{0,2}\b',

    # Tags without dash: P104, HX11, BL07
    r'\b[A-Z]{1,3}\d{2,4}[A-Z]?\b',
]

# Keywords that indicate a P&ID drawing
PID_FILENAME_KEYWORDS = [
    'pid', 'p&id', 'p_id', 'piping', 'instrumentation',
    'pfd', 'process flow', 'schematic', 'drawing', 'diagram',
    'isometric', 'layout', 'flow diagram', 'p-id'
]

PID_CONTENT_KEYWORDS = [
    'piping and instrumentation',
    'p&id', 'process flow diagram',
    'instrument tag', 'line number',
    'control valve', 'safety valve',
    'flow transmitter', 'level transmitter',
    'pressure transmitter', 'temperature transmitter',
    'oisd', 'peso', 'isc', 'isa'
]

# Tags to ignore — common false positives
IGNORE_TAGS = {
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
    'OK', 'NO', 'NA', 'TO', 'OF', 'IN', 'IS',
    'PDF', 'REV', 'DWG', 'DRG', 'SHT', 'STD',
}


# ── Detection ─────────────────────────────────────────────────
def is_pid_drawing(file_path):
    """
    Heuristic check — is this file likely a P&ID?
    Returns True if filename or content suggests a P&ID drawing.
    """
    filename = os.path.basename(file_path).lower()

    # Check filename keywords
    if any(kw in filename for kw in PID_FILENAME_KEYWORDS):
        return True

    # Check content of first page
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        try:
            doc = fitz.open(file_path)
            first_page_text = doc[0].get_text().lower()
            doc.close()
            if any(kw in first_page_text for kw in PID_CONTENT_KEYWORDS):
                return True
            # High density of instrument-style tags is also a signal
            tags = _extract_tags_from_text(first_page_text.upper())
            if len(tags) > 10:
                return True
        except Exception:
            pass

    return False


# ── Tag Extraction ────────────────────────────────────────────
def _extract_tags_from_text(text):
    """
    Extract all equipment and instrument tags from text using regex.
    Returns deduplicated sorted list of tags.
    """
    found = set()
    for pattern in TAG_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            # Skip obvious false positives
            base = match.split('-')[0] if '-' in match else re.match(r'[A-Z]+', match).group()
            if base not in IGNORE_TAGS and len(match) >= 3:
                found.add(match.strip())
    return sorted(found)


def _classify_tag(tag):
    """
    Classify a tag as equipment or instrument based on prefix.
    Returns 'equipment_tag' or 'instrument_tag'
    """
    instrument_prefixes = {
        'FI', 'FT', 'FC', 'FIC', 'FE', 'FF', 'FQ',   # Flow
        'LI', 'LT', 'LC', 'LIC', 'LE', 'LS', 'LSH', 'LSL',  # Level
        'PI', 'PT', 'PC', 'PIC', 'PE', 'PS', 'PSH', 'PSL', 'PSHH',  # Pressure
        'TI', 'TT', 'TC', 'TIC', 'TE', 'TS', 'TSH', 'TSL',  # Temperature
        'AI', 'AT', 'AC', 'AIC',  # Analysis
        'SI', 'ST', 'SC', 'SIC',  # Speed
        'XI', 'XT', 'XC',         # Position
        'ZI', 'ZT', 'ZC',         # Position/stroke
        'HI', 'HO', 'HS',         # Hand/manual
        'SV', 'SOV', 'MOV', 'AOV', 'HOV', 'GOV',  # Valves (actuated)
        'PRV', 'PSV', 'SRV',      # Safety/relief valves
        'CV', 'FCV', 'LCV', 'PCV', 'TCV',  # Control valves
    }

    equipment_prefixes = {
        'P', 'PU',    # Pumps
        'C', 'CP',    # Compressors
        'T', 'TK',    # Tanks/vessels
        'V', 'VE',    # Vessels
        'E', 'HX',    # Heat exchangers
        'B', 'BL',    # Boilers/blowers
        'K',          # Compressors
        'G', 'GEN',   # Generators
        'M', 'MO',    # Motors
        'F', 'FI',    # Filters (non-instrument)
        'AG', 'AC',   # Air compressors
        'CT',         # Cooling towers
        'MV', 'XV',   # Valves (manual)
    }

    prefix = re.match(r'^([A-Z]+)', tag)
    if prefix:
        p = prefix.group(1)
        if p in instrument_prefixes:
            return 'instrument_tag'
        if p in equipment_prefixes:
            return 'equipment_tag'

    return 'equipment_tag'  # default


# ── OCR ──────────────────────────────────────────────────────
def _ocr_page(page, dpi=300):
    """OCR a PDF page at high DPI for scanned P&IDs."""
    try:
        import pytesseract
        import numpy as np
        from PIL import Image as PILImage

        # Check Windows path
        win_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(win_path):
            pytesseract.pytesseract.tesseract_cmd = win_path

        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Use PSM 6 (uniform block of text) for P&IDs
        text = pytesseract.image_to_string(img, config='--psm 6')
        return text.strip()

    except ImportError:
        print("  ⚠ pytesseract not installed — skipping OCR fallback")
        return ""
    except Exception as e:
        print(f"  ⚠ OCR failed: {e}")
        return ""


# ── Main Extractor ────────────────────────────────────────────
def process_pid(file_path):
    """
    Main entry point for P&ID extraction.

    Returns standard document format:
    {
      "doc_id": str,
      "filename": str,
      "doc_type": "pid_drawing",
      "pages": [{page_num, text, tables, ...}],
      "pid_tags": {
          "equipment_tags": [...],
          "instrument_tags": [...],
          "all_tags": [...]
      }
    }
    """
    ext = os.path.splitext(file_path)[1].lower()
    pages_out = []
    all_tags = []

    print(f"  Processing P&ID: {os.path.basename(file_path)}")

    if ext == '.pdf':
        doc = fitz.open(file_path)

        for i, page in enumerate(doc):
            # Try digital text first
            digital_text = page.get_text().strip()
            word_count = len(digital_text.split())

            if word_count >= 20:
                # Good digital text layer
                text = digital_text
                method = "digital"
            else:
                # Scanned page — use OCR
                print(f"  Page {i+1}: sparse text ({word_count} words) → using OCR")
                text = _ocr_page(page)
                method = "ocr"

            # Extract tags from this page
            page_tags = _extract_tags_from_text(text)
            all_tags.extend(page_tags)

            pages_out.append(make_page(
                page_num=i + 1,
                text=text,
                tables=[],
                ocr_confidence=None,
                extra_meta={
                    "extraction_method": f"pid_{method}",
                    "source_type": "pid_drawing",
                    "tags_on_page": page_tags,
                    "tag_count": len(page_tags),
                }
            ))

        doc.close()

    elif ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
        # Image P&ID — use OCR directly
        try:
            import pytesseract
            from PIL import Image as PILImage

            win_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(win_path):
                pytesseract.pytesseract.tesseract_cmd = win_path

            img = PILImage.open(file_path)
            text = pytesseract.image_to_string(img, config='--psm 6')
            page_tags = _extract_tags_from_text(text)
            all_tags.extend(page_tags)

            pages_out.append(make_page(
                page_num=1,
                text=text.strip(),
                tables=[],
                ocr_confidence=None,
                extra_meta={
                    "extraction_method": "pid_ocr_image",
                    "source_type": "pid_drawing",
                    "tags_on_page": page_tags,
                }
            ))
        except Exception as e:
            print(f"  ❌ Image P&ID OCR failed: {e}")

    # Deduplicate and classify all tags
    unique_tags = list(set(all_tags))
    equipment_tags = [t for t in unique_tags if _classify_tag(t) == 'equipment_tag']
    instrument_tags = [t for t in unique_tags if _classify_tag(t) == 'instrument_tag']

    print(f"  ✅ Found {len(equipment_tags)} equipment tags, "
          f"{len(instrument_tags)} instrument tags")

    # Build result in standard doc format
    result = make_doc_shell(file_path, "pid_drawing")
    result["pages"] = pages_out
    result["pid_tags"] = {
        "equipment_tags": sorted(equipment_tags),
        "instrument_tags": sorted(instrument_tags),
        "all_tags": sorted(unique_tags),
    }

    return result