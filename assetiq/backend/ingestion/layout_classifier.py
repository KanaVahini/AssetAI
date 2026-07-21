"""
layout_classifier.py
---------------------
Peer to pid_extractor.py's is_pid_drawing(). Where that function answers
"is this page a P&ID?", this one answers the more general question every
mixed technical document (reports, theses, scanned papers, manuals) needs
answered per-page: "what KIND of content is on this page, and in what mix?"

A single page like the ones in a scanned engineering report commonly
contains two or three of: body prose, a bordered data table, a labeled
line-diagram, and an embedded photo -- all at once. Routing the whole page
to one extractor (pure OCR, or pure table logic) throws away structure.
This module segments the page into typed regions FIRST, so each region can
be handed to the extractor built for it (table_extractor.py /
figure_extractor.py / plain text extraction).

Dependencies: pip install pymupdf opencv-python-headless numpy
"""

import fitz
import cv2
import numpy as np


REGION_TYPES = ("prose", "table", "figure", "photo")


def page_to_gray(page, scale=2.0):
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2GRAY), scale


def has_text_layer(page):
    return len(page.get_text("words")) > 0


# ---------------------------------------------------------------------------
# Region candidates via morphological structure, not just edge density.
# Tables and diagrams both have "lines" -- what separates them is whether
# those lines form a regular grid (table) or an irregular assembly (diagram).
# ---------------------------------------------------------------------------

def find_table_regions(gray):
    """
    Detects bordered/ruled table regions by isolating long horizontal AND
    long vertical strokes separately (morphological opening with long thin
    kernels), then finding where they overlap into a grid. This is the
    standard "ruling line" approach used by most classical table detectors
    (Camelot's lattice mode, OpenCV table-extraction tutorials) and works
    well on scanned pages with visible cell borders -- like a spec table
    with a drawn grid.
    """
    bw = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                cv2.THRESH_BINARY, 15, -2)

    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(gray.shape[1] // 30, 20), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(gray.shape[0] // 30, 20)))

    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel, iterations=1)
    vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel, iterations=1)
    grid = cv2.bitwise_and(cv2.dilate(horiz, np.ones((3, 3), np.uint8)),
                            cv2.dilate(vert, np.ones((3, 3), np.uint8)))

    contours, _ = cv2.findContours(cv2.dilate(grid, np.ones((15, 15), np.uint8)),
                                    cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        # need enough grid-intersection mass inside the box to be a real table,
        # not just a stray pair of crossing lines
        density = cv2.countNonZero(grid[y:y + h, x:x + w]) / max(w * h, 1)
        if w > 80 and h > 60 and density > 0.01:
            regions.append({"bbox": (x, y, x + w, y + h), "grid_density": float(density)})
    return regions


def find_photo_regions(gray, page):
    """
    Embedded raster images (photographs, halftones) are the easy case --
    PDF stores them as XObjects, so we don't need CV guessing for a vector
    PDF. For a fully rasterized/scanned page (no XObjects because the whole
    page IS one big image -- true for every page in an OKEN-scanner-style
    document, this project's sample PDF included), fall back to
    local-variance texture detection: photos have continuous tonal
    gradients, line-art has near-binary black/white with sparse ink -- so a
    high-variance, high-fill-ratio patch is a candidate halftone photo.

    TESTED LIMITATION: run against a real photo page from this project's
    sample PDF, this heuristic under-detects -- a halftone photo
    reproduced by a low-quality photocopier/scanner can end up with
    variance and ink-fill statistics close enough to a text paragraph's
    that the two aren't reliably separable at the window scale used here.
    It also has no notion of "this region is one coherent photo" -- it
    just flags scattered small patches. Don't treat this as production-
    ready photo detection; it's a starting point.

    For real reliability here, the credible fix is a trained document-
    layout model rather than more classical-CV parameter tuning --
    e.g. `pip install layoutparser` with a PubLayNet-pretrained Detectron2
    model (classes: Text / Title / List / Table / Figure), or PaddleOCR's
    PP-StructureV2 layout analyzer. Swap either in here behind the same
    return shape ([{"bbox": (x0,y0,x1,y1), "source": ...}, ...]) and
    nothing downstream (caption/legend matching) needs to change -- same
    "classical baseline now, swap in the trained model later" pattern
    pid_extractor.py already uses for symbol detection.
    """
    regions = []
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        for r in rects:
            regions.append({"bbox": (r.x0, r.y0, r.x1, r.y1), "source": "xobject"})

    if regions:
        return regions

    # Rasterized-page fallback: sliding-window local variance + ink fill ratio.
    h, w = gray.shape
    step = max(h // 12, 40)
    win = step * 2
    for y in range(0, h - win, step):
        for x in range(0, w - win, step):
            patch = gray[y:y + win, x:x + win]
            variance = float(np.var(patch))
            ink_ratio = float(np.mean(patch < 200))
            # photos: lots of mid-tone variance and moderate-to-high ink coverage;
            # clean line-art/prose: low variance, low ink coverage (mostly white)
            if variance > 1800 and 0.25 < ink_ratio < 0.85:
                regions.append({"bbox": (x, y, x + win, y + win), "source": "texture"})
    return _merge_overlapping(regions)


def find_diagram_regions(gray, table_regions, photo_regions):
    """
    Whatever has a dense cluster of straight lines but ISN'T a table grid
    and ISN'T a photo is treated as a line-diagram/figure (schematics,
    labeled assembly drawings, flowcharts). Line-dense connected regions,
    minus the areas already claimed by tables/photos.
    """
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                             minLineLength=25, maxLineGap=6)
    if lines is None:
        return []

    mask = np.zeros_like(gray)
    for x1, y1, x2, y2 in lines[:, 0]:
        cv2.line(mask, (x1, y1), (x2, y2), 255, 2)

    for claimed in table_regions + photo_regions:
        x0, y0, x1, y1 = [int(v) for v in claimed["bbox"]]
        mask[y0:y1, x0:x1] = 0

    dilated = cv2.dilate(mask, np.ones((25, 25), np.uint8))
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        line_px = cv2.countNonZero(mask[y:y + h, x:x + w])
        if w > 60 and h > 60 and line_px > 300:
            regions.append({"bbox": (x, y, x + w, y + h), "line_pixels": int(line_px)})
    return regions


def _merge_overlapping(regions, iou_thresh=0.15):
    if not regions:
        return []
    boxes = [r["bbox"] for r in regions]
    merged = []
    used = [False] * len(boxes)
    for i, b in enumerate(boxes):
        if used[i]:
            continue
        x0, y0, x1, y1 = b
        for j in range(i + 1, len(boxes)):
            if used[j]:
                continue
            if _iou(b, boxes[j]) > iou_thresh:
                bx0, by0, bx1, by1 = boxes[j]
                x0, y0, x1, y1 = min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)
                used[j] = True
        merged.append({"bbox": (x0, y0, x1, y1)})
    return merged


def _iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / union


def classify_page_regions(file_path, page_index, scale=2.0):
    """
    Main entry point. Returns:
        {
          "page_index": int,
          "scale": float,               # pixel-to-PDF-point scale used
          "has_text_layer": bool,
          "table_regions": [...],
          "photo_regions": [...],
          "diagram_regions": [...],
          "page_type": "prose"|"table"|"figure"|"photo"|"mixed"
        }
    All bboxes are in PIXEL coords at the given scale -- callers divide by
    `scale` to convert back to PDF point space shared with text bboxes.
    """
    doc = fitz.open(file_path)
    page = doc[page_index]
    gray, used_scale = page_to_gray(page, scale)

    tables = find_table_regions(gray)
    photos = find_photo_regions(gray, page)
    diagrams = find_diagram_regions(gray, tables, photos)

    types_present = set()
    if tables:
        types_present.add("table")
    if photos:
        types_present.add("photo")
    if diagrams:
        types_present.add("figure")
    if not types_present:
        types_present.add("prose")

    page_type = types_present.pop() if len(types_present) == 1 else "mixed"

    return {
        "page_index": page_index,
        "scale": used_scale,
        "has_text_layer": has_text_layer(page),
        "table_regions": tables,
        "photo_regions": photos,
        "diagram_regions": diagrams,
        "page_type": page_type,
    }
