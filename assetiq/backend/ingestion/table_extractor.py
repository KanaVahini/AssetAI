"""
table_extractor.py
-------------------
Consumes the `table_regions` produced by layout_classifier.py and turns
each ruled-grid bbox into an actual list-of-rows structure, instead of the
flat token soup you'd get from pdf_extractor.py or ocr_extractor.py on the
same page.

Two paths:
  - VECTOR path: page has a real text layer -> read words inside the region
    bbox, cluster by row (y-position) then by column (x-position gaps).
  - OCR path: scanned page, no text layer -> re-run the same grid-line
    detection at higher res to get individual cell boxes, OCR each cell
    independently (this is far more reliable than OCR-ing the whole table
    as one blob, which is what happens if you just hand a table region to
    ocr_extractor.py directly).

Dependencies: pip install pymupdf opencv-python-headless numpy
Optional: pip install pytesseract   (only needed for the OCR path)
Recommended for scanned tables: pip install img2table   (see note below)

IMPORTANT -- tested against a real scanned page from this project's sample
PDF (a spec table with faint, fold-creased ruling lines): the classical
morphological grid-line detector below (extract_table_ocr's inner-grid
step) is UNRELIABLE on this kind of scan. Thin ruling lines that are
gray rather than solid black, or broken by a paper fold, fall below
threshold no matter how the adaptiveThreshold/kernel parameters are
tuned -- I ran it against the actual document and it missed most interior
row lines. Treat extract_table_ocr as a fallback for clean, high-contrast
scans only.

For real scanned-table reliability, use extract_tables_img2table() below
instead -- it wraps img2table, which combines OCR word positions with a
more tolerant line-detection pass (and doesn't require the grid to be
fully unbroken). This is the same "classical baseline now, swap in the
real thing" pattern pid_extractor.py uses for symbol detection -- install
it with: pip install img2table
"""

import fitz
import cv2
import numpy as np


def extract_table_vector(file_path, page_index, bbox_px, scale):
    """
    bbox_px: (x0,y0,x1,y1) in pixel coords at `scale` (as produced by
    layout_classifier). Converts to PDF point space, pulls words inside it,
    and reconstructs rows/columns by clustering positions.
    """
    doc = fitz.open(file_path)
    page = doc[page_index]
    x0, y0, x1, y1 = [v / scale for v in bbox_px]

    words = [w for w in page.get_text("words")
             if w[0] >= x0 - 2 and w[2] <= x1 + 2 and w[1] >= y0 - 2 and w[3] <= y1 + 2]
    if not words:
        return None

    return _words_to_grid(words)


def _words_to_grid(words, row_tol=4.0, col_gap_factor=2.5):
    """
    words: list of (x0,y0,x1,y1,text,...) tuples from page.get_text("words").
    Clusters into rows by y-center proximity, then within each row splits
    into columns wherever the horizontal gap between consecutive words
    exceeds `col_gap_factor` times the median word gap on the page --i.e.
    a real column boundary reads as a much bigger gap than normal word
    spacing within one cell's text.
    """
    words = sorted(words, key=lambda w: (round(w[1] / row_tol), w[0]))
    rows = []
    current_row, current_y = [], None
    for w in words:
        yc = (w[1] + w[3]) / 2
        if current_y is None or abs(yc - current_y) <= row_tol:
            current_row.append(w)
            current_y = yc if current_y is None else current_y
        else:
            rows.append(current_row)
            current_row, current_y = [w], yc
    if current_row:
        rows.append(current_row)

    all_gaps = []
    for row in rows:
        row_sorted = sorted(row, key=lambda w: w[0])
        for a, b in zip(row_sorted, row_sorted[1:]):
            all_gaps.append(b[0] - a[2])
    median_gap = float(np.median(all_gaps)) if all_gaps else 5.0
    col_break = max(median_gap * col_gap_factor, 8.0)

    grid = []
    for row in rows:
        row_sorted = sorted(row, key=lambda w: w[0])
        cells, current_cell = [], [row_sorted[0][4]]
        for a, b in zip(row_sorted, row_sorted[1:]):
            if (b[0] - a[2]) > col_break:
                cells.append(" ".join(current_cell))
                current_cell = [b[4]]
            else:
                current_cell.append(b[4])
        cells.append(" ".join(current_cell))
        grid.append(cells)
    return grid


def extract_table_ocr(file_path, page_index, bbox_px, scale, dpi_scale=3.0):
    """
    OCR path for scanned tables. Re-detects the fine grid lines inside the
    region at higher resolution to get per-cell boxes, then OCRs each cell
    separately -- this avoids Tesseract trying to guess column structure
    from a single undifferentiated crop, which is the usual failure mode
    for OCR-ing whole tables at once.
    """
    try:
        import pytesseract
    except ImportError:
        raise RuntimeError("OCR table path requires: pip install pytesseract")

    doc = fitz.open(file_path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi_scale, dpi_scale))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2GRAY)

    rescale = dpi_scale / scale
    x0, y0, x1, y1 = [int(v * rescale) for v in bbox_px]
    crop = gray[max(y0, 0):y1, max(x0, 0):x1]
    if crop.size == 0:
        return None

    bw = cv2.adaptiveThreshold(~crop, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(crop.shape[1] // 25, 15), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(crop.shape[0] // 25, 15)))
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel)
    vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel)

    row_lines = sorted(_line_positions(horiz, axis=0))
    col_lines = sorted(_line_positions(vert, axis=1))
    if len(row_lines) < 2 or len(col_lines) < 2:
        # no reliable inner grid found -- fall back to whole-crop OCR as one blob,
        # caller should treat this as lower-confidence
        text = pytesseract.image_to_string(crop).strip()
        return [[text]] if text else None

    grid = []
    for ry0, ry1 in zip(row_lines, row_lines[1:]):
        row = []
        for cx0, cx1 in zip(col_lines, col_lines[1:]):
            cell = crop[ry0:ry1, cx0:cx1]
            if cell.size == 0:
                row.append("")
                continue
            txt = pytesseract.image_to_string(cell, config="--psm 6").strip()
            row.append(txt)
        grid.append(row)
    return grid


def _line_positions(binary_line_img, axis, min_gap=10):
    profile = np.sum(binary_line_img > 0, axis=axis)
    threshold = profile.max() * 0.3 if profile.max() > 0 else 1
    positions = np.where(profile > threshold)[0]
    if len(positions) == 0:
        return []
    grouped = [positions[0]]
    for p in positions[1:]:
        if p - grouped[-1] > min_gap:
            grouped.append(p)
    return grouped


def extract_tables_img2table(file_path, page_index):
    """
    RECOMMENDED path for scanned pages -- pip install img2table.
    img2table detects table structure from a rendered page image using a
    combination of contour analysis and OCR word clustering, which
    tolerates broken/faint ruling lines far better than the pure
    morphological approach above (verified need: see module docstring).

    Returns a list of {"bbox_pdf_points": (...), "rows": [[cell,...],...],
    "source": "img2table"} -- same shape as extract_table()'s return value,
    so callers don't need to branch on which path produced it.

    NOTE: this function is written to img2table's documented API but has
    not been executable in this environment (no network access to install
    the package here) -- verify against a sample page before relying on it
    in production, same as any newly-wired dependency.
    """
    from img2table.document import Image as I2TImage
    from img2table.ocr import TesseractOCR

    doc = fitz.open(file_path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
    img_bytes = pix.tobytes("png")

    tmp_path = f"/tmp/_i2t_page_{page_index}.png"
    with open(tmp_path, "wb") as f:
        f.write(img_bytes)

    ocr = TesseractOCR(lang="eng")
    doc_img = I2TImage(src=tmp_path)
    extracted = doc_img.extract_tables(ocr=ocr, implicit_rows=True, borderless_tables=False)

    results = []
    render_scale = 3.0
    for tbl in extracted:
        rows = []
        for row in tbl.content.values():
            rows.append([cell.value or "" for cell in row])
        bbox = tbl.bbox
        pdf_bbox = (bbox.x1 / render_scale, bbox.y1 / render_scale,
                    bbox.x2 / render_scale, bbox.y2 / render_scale)
        results.append({"bbox_pdf_points": pdf_bbox, "rows": rows, "source": "img2table"})
    return results


def extract_table(file_path, page_index, table_region, has_text_layer, scale):
    """
    Dispatch: try vector extraction if the page has a text layer, otherwise
    (or on empty result) fall back to the OCR grid path.
    Returns {"bbox_pdf_points": (...), "rows": [[cell,...],...], "source": str}
    or None if nothing could be extracted.
    """
    bbox_px = table_region["bbox"]
    grid, source = None, None

    if has_text_layer:
        grid = extract_table_vector(file_path, page_index, bbox_px, scale)
        source = "vector"

    if not grid:
        grid = extract_table_ocr(file_path, page_index, bbox_px, scale)
        source = "ocr"

    if not grid:
        return None

    x0, y0, x1, y1 = [v / scale for v in bbox_px]
    return {"bbox_pdf_points": (x0, y0, x1, y1), "rows": grid, "source": source}
