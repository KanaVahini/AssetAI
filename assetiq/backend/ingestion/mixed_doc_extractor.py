"""
mixed_doc_extractor.py
-----------------------
Entry point for reports/papers/manuals that mix body prose, tables, and
labeled diagrams/photos on the same pages -- e.g. a scanned technical paper
like a mining-equipment specification document. Same calling convention as
process_pdf() / process_pid(), so file_router.py can dispatch to it.

Pipeline per page:
  1. layout_classifier.classify_page_regions -> table / diagram / photo boxes
  2. figure_extractor.get_text_blocks        -> all text, block-level (vector or OCR)
  3. table_extractor.extract_table           -> one grid per table region
  4. figure_extractor.process_figures        -> one record per diagram/photo,
                                                 with caption + resolved legend
  5. remaining text blocks (not inside any table/figure bbox) -> "prose"

Dependencies: pip install pymupdf opencv-python-headless numpy
Optional:     pip install pytesseract   (scanned pages / OCR fallback paths)
"""

import os
import fitz
from layout_classifier import classify_page_regions
from table_extractor import extract_table
from figure_extractor import get_text_blocks, process_figures


def _bbox_inside(inner, outer, tol=3):
    ix0, iy0, ix1, iy1 = inner
    ox0, oy0, ox1, oy1 = outer
    return ix0 >= ox0 - tol and iy0 >= oy0 - tol and ix1 <= ox1 + tol and iy1 <= oy1 + tol


def process_page(file_path, page_index):
    layout = classify_page_regions(file_path, page_index)
    scale = layout["scale"]
    text_blocks = get_text_blocks(file_path, page_index)

    tables = []
    for region in layout["table_regions"]:
        t = extract_table(file_path, page_index, region, layout["has_text_layer"], scale)
        if t:
            tables.append(t)

    figures = process_figures(
        file_path, page_index,
        layout["diagram_regions"], layout["photo_regions"],
        scale, text_blocks,
    )

    claimed_bboxes = (
        [t["bbox_pdf_points"] for t in tables] +
        [f["bbox_pdf_points"] for f in figures]
    )

    prose_blocks = [
        tb["text"] for tb in text_blocks
        if not any(_bbox_inside(tb["bbox"], claimed) for claimed in claimed_bboxes)
    ]

    return {
        "page_index":  page_index,
        "page_type":   layout["page_type"],
        "prose":       prose_blocks,
        "tables":      tables,
        "figures":     figures,
    }


def process_document(file_path):
    """
    Returns:
        {
          "doc_type": "mixed_technical_document",
          "source_file": str,
          "pages": [ {page_index, page_type, prose, tables, figures}, ... ]
        }

    Feed straight into graph_builder.py as its own entity type, same
    pattern as pid_extractor.process_pid(): tables become structured
    attribute records, figures/legend entries become part-of relationships,
    prose gets chunked and embedded same as any other document text.
    """
    doc = fitz.open(file_path)
    pages_out = [process_page(file_path, i) for i in range(doc.page_count)]
    doc.close()
    return {
        "doc_type":    "mixed_technical_document",
        "source_file": os.path.basename(file_path),
        "pages":       pages_out,
    }


if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) < 2:
        print("Usage: python mixed_doc_extractor.py <path_to_document.pdf>")
        sys.exit(1)
    result = process_document(sys.argv[1])
    print(json.dumps(result, indent=2, default=str))
