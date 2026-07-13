"""
Minimal smoke tests. Not exhaustive — just enough to catch a handler
returning the wrong shape before it breaks your teammates' code.

Run with: pytest ingestion/tests/test_pipeline.py -v

Drop real sample files into sample_docs/<format>/ before running —
these tests expect at least one file per folder to exist.
"""

import json
from pathlib import Path

import pytest

from ingestion.pipeline import ingest_path, run
from ingestion.utils.enrichment import extract_entities_from_doc

REQUIRED_DOC_KEYS = {"doc_id", "source_path", "doc_type", "ingested_at", "pages", "metadata"}
REQUIRED_PAGE_KEYS = {"page_num", "text", "tables", "ocr_confidence"}

SAMPLE_DIRS = {
    "pdfs": "*.pdf",
    "scanned": "*.pdf",
    "images": "*.png",
    "spreadsheets": "*.csv",
    "emails": "*.eml",
}


def _first_sample(folder: str, pattern: str):
    matches = list(Path(f"sample_docs/{folder}").glob(pattern))
    return matches[0] if matches else None


def _assert_valid_schema(doc: dict):
    assert REQUIRED_DOC_KEYS.issubset(doc.keys()), f"missing doc keys: {REQUIRED_DOC_KEYS - doc.keys()}"
    assert isinstance(doc["pages"], list) and len(doc["pages"]) > 0
    for page in doc["pages"]:
        assert REQUIRED_PAGE_KEYS.issubset(page.keys()), f"missing page keys: {REQUIRED_PAGE_KEYS - page.keys()}"


@pytest.mark.parametrize("folder,pattern", SAMPLE_DIRS.items())
def test_handler_produces_valid_schema(folder, pattern):
    sample = _first_sample(folder, pattern)
    if sample is None:
        pytest.skip(f"no sample file found in sample_docs/{folder} — add one to run this test")

    doc = ingest_path(sample)
    assert doc is not None, f"handler returned None for {sample}"
    _assert_valid_schema(doc)


def test_unsupported_extension_returns_none(tmp_path):
    bad_file = tmp_path / "notes.docx"
    bad_file.write_text("irrelevant")
    assert ingest_path(bad_file) is None


def test_entity_extraction_finds_industrial_terms():
    doc = {
        "source_path": "sample_docs/pdfs/report.pdf",
        "doc_id": "doc-1",
        "doc_type": "pdf_digital",
        "metadata": {"doc_title": "report"},
        "pages": [
            {
                "page_num": 1,
                "text": "Pump P-101 was inspected on 12/07/2026 under OISD 118 by Mr. Ravi Kumar.",
                "tables": [],
                "ocr_confidence": None,
                "metadata": {},
            }
        ],
    }

    entities = extract_entities_from_doc(doc)
    entity_map = {(item["type"], item["value"]): item for item in entities}

    assert ("equipment_tag", "P-101") in entity_map
    assert ("regulatory_reference", "OISD 118") in entity_map or ("regulatory_reference", "OISD") in entity_map
    assert ("date", "12/07/2026") in entity_map
    assert ("person", "Mr. Ravi Kumar") in entity_map
    assert entity_map[("equipment_tag", "P-101")]["citations"]


def test_pipeline_marks_duplicate_documents(tmp_path):
    input_dir = tmp_path / "batch"
    input_dir.mkdir()
    file_one = input_dir / "a.eml"
    file_two = input_dir / "b.eml"
    content = """From: Ravi Kumar <ravi@example.com>
To: plant@example.com
Subject: Inspection note
Date: Mon, 8 Jul 2026 09:00:00 +0530

Pump P-101 inspected on 12/07/2026. OISD 118 applies.
"""
    file_one.write_text(content, encoding="utf-8")
    file_two.write_text(content, encoding="utf-8")

    output_path = tmp_path / "out.jsonl"
    run(str(input_dir), str(output_path))

    docs = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(docs) == 2
    assert docs[0]["is_duplicate"] is False
    assert docs[1]["is_duplicate"] is True
    assert docs[1]["duplicate_of"] == docs[0]["doc_id"]
    assert docs[0]["content_hash"] == docs[1]["content_hash"]
    assert docs[0]["citations"] and docs[0]["entities"]


def test_pipeline_versions_changed_documents_across_runs(tmp_path):
    input_dir = tmp_path / "versions"
    input_dir.mkdir()
    file_path = input_dir / "report.eml"
    output_path = tmp_path / "versioned.jsonl"

    file_path.write_text(
        """From: Ravi Kumar <ravi@example.com>
Subject: Initial report

Pump P-101 inspected.
""",
        encoding="utf-8",
    )
    run(str(input_dir), str(output_path))

    file_path.write_text(
        """From: Ravi Kumar <ravi@example.com>
Subject: Updated report

Pump P-101 inspected and repaired.
""",
        encoding="utf-8",
    )
    run(str(input_dir), str(output_path))

    docs = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(docs) == 1
    assert docs[0]["version"] == 2
    assert docs[0]["metadata"]["source_type"] == "email"
    assert docs[0]["pages"][0]["citations"]
