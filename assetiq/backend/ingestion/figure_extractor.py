"""
figure_extractor.py
--------------------
Consumes `diagram_regions` and `photo_regions` from layout_classifier.py and
turns each into a usable record: crop, type, nearest caption, and -- for
labeled assembly/schematic drawings specifically -- a resolved legend
mapping (e.g. the BWE cutaway diagram's "A, B, C... N" callouts next to a
text list "A Wheel / B Bucket / C Wheel Boom...").

This is the piece a generic OCR pass structurally cannot give you: OCR
alone returns "A" and "Wheel" as two independent text blobs on the page
with no indication that A labels the wheel in the drawing above. Solving
that requires spatial reasoning across the callout mark, the drawing, and
the legend list -- which is what this module does.

Dependencies: pip install pymupdf opencv-python-headless numpy
Optional: pip install pytesseract   (only needed if the page has no text layer)
"""

import re
import math
import fitz
import cv2
import numpy as np


CAPTION_PATTERNS = re.compile(
    r'^\s*(fig(ure)?\.?|table)\s*[\d.]*[:.\-]?\s*', re.IGNORECASE
)

# Matches a legend LIST line like "A  Wheel" or "H  Discharge Boom" -- a
# single leading capital letter/number token, then a short label.
LEGEND_LINE = re.compile(r'^\s*([A-Z]|\d{1,2})\s+([A-Za-z][A-Za-z /\-]{2,40})\s*$')


def crop_region(file_path, page_index, bbox_px, scale, render_scale=2.5):
    doc = fitz.open(file_path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(render_scale, render_scale))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    r = render_scale / scale
    x0, y0, x1, y1 = [int(v * r) for v in bbox_px]
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, img.shape[1]), min(y1, img.shape[0])
    return img[y0:y1, x0:x1]


def get_text_blocks(file_path, page_index):
    """
    Block-level text with position and simple style signal (font size),
    which caption-matching and legend-matching both key off. Falls back to
    OCR line grouping when there's no vector text layer.
    """
    doc = fitz.open(file_path)
    page = doc[page_index]
    raw = page.get_text("dict")
    blocks = []
    for b in raw.get("blocks", []):
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            sizes = [span["size"] for span in line["spans"]]
            bbox = line["bbox"]
            blocks.append({"text": text, "bbox": bbox, "font_size": max(sizes)})
    if blocks:
        return blocks

    try:
        import pytesseract
    except ImportError:
        return []
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2GRAY)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    lines = {}
    for i, txt in enumerate(data["text"]):
        if not txt.strip():
            continue
        key = (data["block_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append((data["left"][i], data["top"][i],
                                           data["width"][i], data["height"][i], txt))
    for parts in lines.values():
        xs0 = min(p[0] for p in parts) / 2.0
        ys0 = min(p[1] for p in parts) / 2.0
        xs1 = max(p[0] + p[2] for p in parts) / 2.0
        ys1 = max(p[1] + p[3] for p in parts) / 2.0
        text = " ".join(p[4] for p in parts)
        blocks.append({"text": text, "bbox": (xs0, ys0, xs1, ys1), "font_size": None})
    return blocks


def find_caption(figure_bbox_pts, text_blocks, max_dist=60):
    """
    Caption heuristic: prefer a text block that (a) matches an explicit
    "Figure"/"Table" pattern, else (b) is the closest short text block
    directly below the figure, within max_dist points -- the common layout
    convention this document also follows (bold labels like "Mobile
    Transfer Conveyor" sitting right under the photo).
    """
    fx0, fy0, fx1, fy1 = figure_bbox_pts
    fcx = (fx0 + fx1) / 2
    candidates = []
    for tb in text_blocks:
        tx0, ty0, tx1, ty1 = tb["bbox"]
        tcx = (tx0 + tx1) / 2
        below = ty0 >= fy1 - 5
        horizontally_aligned = abs(tcx - fcx) < (fx1 - fx0) / 2 + 40
        vertical_gap = ty0 - fy1
        if below and horizontally_aligned and 0 <= vertical_gap <= max_dist:
            score = vertical_gap + (0 if CAPTION_PATTERNS.match(tb["text"]) else 15)
            candidates.append((score, tb["text"]))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return CAPTION_PATTERNS.sub("", candidates[0][1]).strip()


# ---------------------------------------------------------------------------
# Legend / callout resolution
# ---------------------------------------------------------------------------

def detect_callout_marks(gray_crop):
    """
    Finds small circled-letter/number callout marks inside a diagram crop:
    a small near-circular contour with a single character in the middle.
    Returns [{"bbox": (x0,y0,x1,y1), "center": (cx,cy)}] in crop-local
    pixel coords. The character itself is read separately via OCR on the
    small patch, since Hough-circle detection alone doesn't give you text.
    """
    edges = cv2.Canny(gray_crop, 60, 160)
    circles = cv2.HoughCircles(
        cv2.medianBlur(gray_crop, 3), cv2.HOUGH_GRADIENT, dp=1.2, minDist=15,
        param1=80, param2=22, minRadius=6, maxRadius=18,
    )
    marks = []
    if circles is not None:
        for cx, cy, r in circles[0]:
            marks.append({
                "bbox": (cx - r, cy - r, cx + r, cy + r),
                "center": (float(cx), float(cy)),
            })
    return marks


def read_callout_labels(gray_crop, marks):
    try:
        import pytesseract
    except ImportError:
        return marks
    for m in marks:
        x0, y0, x1, y1 = [int(v) for v in m["bbox"]]
        x0, y0 = max(x0, 0), max(y0, 0)
        patch = gray_crop[y0:y1, x0:x1]
        if patch.size == 0:
            continue
        patch = cv2.resize(patch, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        txt = pytesseract.image_to_string(
            patch, config="--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        ).strip()
        m["label"] = txt[:1] if txt else None
    return marks


def find_legend_list(text_blocks, figure_bbox_pts, search_radius=250):
    """
    Legend lists in this kind of document appear as a short vertical run of
    "<letter> <term>" lines near the figure (either beside it in two
    columns, as in the BWE cutaway page, or below it). Collect nearby
    blocks matching LEGEND_LINE and return {letter: term}.
    """
    fx0, fy0, fx1, fy1 = figure_bbox_pts
    fcx, fcy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    legend = {}
    for tb in text_blocks:
        tx0, ty0, tx1, ty1 = tb["bbox"]
        tcx, tcy = (tx0 + tx1) / 2, (ty0 + ty1) / 2
        if math.dist((fcx, fcy), (tcx, tcy)) > search_radius:
            continue
        m = LEGEND_LINE.match(tb["text"])
        if m:
            legend[m.group(1).upper()] = m.group(2).strip()
    return legend


def resolve_diagram_legend(file_path, page_index, diagram_region, scale, text_blocks):
    """
    Full pipeline for one diagram region: detect callout marks, OCR each
    mark's character, match against a nearby legend list, and return a
    part-name-resolved structure -- e.g. for the BWE cutaway:
        {"A": "Wheel", "B": "Bucket", "C": "Wheel Boom", ...}
    plus any callouts that couldn't be matched to a legend entry.
    """
    bbox_px = diagram_region["bbox"]
    doc = fitz.open(file_path)
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2GRAY)

    x0, y0, x1, y1 = [int(v) for v in bbox_px]
    crop = gray[max(y0, 0):y1, max(x0, 0):x1]
    if crop.size == 0:
        return {"resolved": {}, "unmatched_callouts": []}

    marks = detect_callout_marks(crop)
    marks = read_callout_labels(crop, marks)

    bbox_pts = tuple(v / scale for v in bbox_px)
    legend = find_legend_list(text_blocks, bbox_pts)

    resolved, unmatched = {}, []
    for m in marks:
        label = m.get("label")
        if label and label in legend:
            resolved[label] = legend[label]
        else:
            unmatched.append(m)
    return {"resolved": resolved, "unmatched_callouts": [
        {"center": m["center"], "label_guess": m.get("label")} for m in unmatched
    ]}


def process_figures(file_path, page_index, diagram_regions, photo_regions, scale, text_blocks):
    """
    Main entry point for one page's worth of figures. Returns a list of:
        {
          "type": "diagram" | "photo",
          "bbox_pdf_points": (...),
          "caption": str | None,
          "legend": {...} | None,        # diagrams only, if any callouts found
        }
    """
    results = []
    for region in diagram_regions:
        bbox_pts = tuple(v / scale for v in region["bbox"])
        caption = find_caption(bbox_pts, text_blocks)
        legend_info = resolve_diagram_legend(file_path, page_index, region, scale, text_blocks)
        results.append({
            "type": "diagram",
            "bbox_pdf_points": bbox_pts,
            "caption": caption,
            "legend": legend_info["resolved"] or None,
            "unmatched_callouts": legend_info["unmatched_callouts"],
        })

    for region in photo_regions:
        bbox_pts = tuple(v / scale for v in region["bbox"])
        caption = find_caption(bbox_pts, text_blocks)
        results.append({
            "type": "photo",
            "bbox_pdf_points": bbox_pts,
            "caption": caption,
        })

    return results
