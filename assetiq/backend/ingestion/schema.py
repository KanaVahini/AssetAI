"""
Single source of truth for the ingestion output shape.
Every handler MUST return a dict built with make_doc_shell() + pages
appended via make_page(). Do not hand-roll dicts elsewhere — if the
schema needs a new field, add it here so every handler and every
downstream consumer (entity extraction, KG, RAG) stays in sync.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_doc_shell(source_path, doc_type: str) -> dict:
    """
    doc_type must be one of:
    'pdf_digital' | 'pdf_scanned' | 'image' | 'csv' | 'xlsx' | 'email'
    """
    return {
        "doc_id": str(uuid.uuid4()),
        "source_path": str(source_path),
        "doc_type": doc_type,
        "ingested_at": now_iso(),
        "pages": [],
        "metadata": {
            "doc_title": Path(source_path).stem,
            "source_extension": Path(source_path).suffix.lower(),
            "source_type": doc_type,
        },
        "entities": [],
        "citations": [],
        "content_hash": None,
        "version": 1,
        "is_duplicate": False,
        "duplicate_of": None,
    }


def make_page(page_num: int, text: str, tables: list = None, ocr_confidence=None, extra_meta: dict = None, citations: list = None) -> dict:
    page = {
        "page_num": page_num,
        "text": text or "",
        "tables": tables or [],
        "ocr_confidence": ocr_confidence,  # float 0-1, or None if not OCR'd
        "citations": citations or [],
    }
    if extra_meta:
        page["metadata"] = extra_meta
    return page
