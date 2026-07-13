"""
Lightweight document enrichment for industrial ingestion.

This module keeps the heuristics centralized so handlers only need to
return normalized text/tables/metadata, and the pipeline can enrich the
document with entities, citations, and dedup/version information.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from hashlib import sha256
from email.utils import getaddresses
from pathlib import Path
from typing import Iterable


EQUIPMENT_TAG_RE = re.compile(
    r"\b(?:[A-Z]{1,6}[-/]?\d{1,5}[A-Z]?(?:[-/]\d{1,3})?|"
    r"[A-Z]{1,4}-[A-Z]{1,4}-\d{1,5}[A-Z]?|"
    r"[A-Z]{1,6}\d{2,5}[A-Z]?)\b"
)
REGULATORY_REF_RE = re.compile(
    r"\b(?:Factory Act|Factories Act|OISD(?:\s*[-/]?\s*\d+)?|PESO|BIS|ISO\s*\d+(?:-\d+)?|"
    r"IS\s*\d+(?:-\d+)?|IEC\s*\d+(?:-\d+)?|NFPA\s*\d+|Environmental?\s+Clearance|"
    r"Pollution\s+Control\s+Board|Hazardous\s+Waste\s+Rules)\b",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4}|\d{1,2}\s+[A-Z][a-z]{2,8}\s+\d{4}|"
    r"[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4}|\d{1,2}[/-][A-Z][a-z]{2,8}[/-]\d{2,4})\b"
)
PERSON_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Engr|Engineer|Shri|Smt)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b"
)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _iter_text_sources(doc: dict) -> Iterable[tuple[int, str, dict]]:
    for page in doc.get("pages", []):
        yield page.get("page_num", 1), page.get("text", "") or "", page.get("metadata", {}) or {}


def _add_entity(store: OrderedDict, entity_type: str, value: str, citation: dict):
    key = (entity_type, value)
    if key not in store:
        store[key] = {
            "type": entity_type,
            "value": value,
            "occurrences": 0,
            "citations": [],
        }
    store[key]["occurrences"] += 1
    if citation not in store[key]["citations"]:
        store[key]["citations"].append(citation)


def _line_citation(doc: dict, page_num: int, locator: str, snippet: str) -> dict:
    citation = {
        "source_path": doc.get("source_path"),
        "doc_id": doc.get("doc_id"),
        "doc_type": doc.get("doc_type"),
        "page_num": page_num,
        "locator": locator,
        "excerpt": _normalize_whitespace(snippet)[:220],
    }
    return citation


def extract_entities_from_doc(doc: dict) -> list[dict]:
    entities: OrderedDict = OrderedDict()

    for page_num, text, page_meta in _iter_text_sources(doc):
        lines = [line for line in (text or "").splitlines() if line.strip()]
        if not lines and text:
            lines = [text]

        for raw_line in lines:
            line = _normalize_whitespace(raw_line)
            if not line:
                continue

            citation = _line_citation(doc, page_num, page_meta.get("sheet_name") or f"page {page_num}", line)

            for match in EQUIPMENT_TAG_RE.finditer(line):
                value = match.group(0)
                if REGULATORY_REF_RE.fullmatch(value):
                    continue
                _add_entity(entities, "equipment_tag", value, citation)

            for match in REGULATORY_REF_RE.finditer(line):
                _add_entity(entities, "regulatory_reference", _normalize_whitespace(match.group(0)), citation)

            for match in DATE_RE.finditer(line):
                _add_entity(entities, "date", _normalize_whitespace(match.group(0)), citation)

            for match in PERSON_RE.finditer(line):
                _add_entity(entities, "person", _normalize_whitespace(match.group(0)), citation)

    metadata = doc.get("metadata", {}) or {}
    for header_key in ("from", "to"):
        values = metadata.get(header_key)
        if not values:
            continue
        header_values = values if isinstance(values, list) else [values]
        for name, email_address in getaddresses(header_values):
            candidate = _normalize_whitespace(name)
            if candidate:
                citation = _line_citation(doc, 1, f"email header: {header_key}", candidate)
                _add_entity(entities, "person", candidate, citation)
            elif email_address:
                citation = _line_citation(doc, 1, f"email header: {header_key}", email_address)
                _add_entity(entities, "email_address", email_address.lower(), citation)

    return list(entities.values())


def attach_citations(doc: dict) -> dict:
    citations = []
    for page in doc.get("pages", []):
        page_num = page.get("page_num", 1)
        page_meta = page.get("metadata", {}) or {}
        locator = page_meta.get("sheet_name") or f"page {page_num}"
        excerpt = _normalize_whitespace(page.get("text", ""))[:220]
        citation = {
            "source_path": doc.get("source_path"),
            "doc_id": doc.get("doc_id"),
            "doc_type": doc.get("doc_type"),
            "page_num": page_num,
            "locator": locator,
            "excerpt": excerpt,
        }
        page["citations"] = [citation]
        citations.append(citation)

    doc["citations"] = citations
    return doc


def enrich_entities(doc: dict) -> dict:
    doc["entities"] = extract_entities_from_doc(doc)
    return doc


def compute_content_hash(doc: dict) -> str:
    payload = {
        "source_path": str(doc.get("source_path", "")),
        "doc_type": doc.get("doc_type"),
        "metadata": doc.get("metadata", {}),
        "pages": [],
    }

    for page in doc.get("pages", []):
        payload["pages"].append(
            {
                "page_num": page.get("page_num"),
                "text": page.get("text", ""),
                "tables": page.get("tables", []),
                "metadata": page.get("metadata", {}),
                "ocr_confidence": page.get("ocr_confidence"),
            }
        )

    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(blob.encode("utf-8")).hexdigest()


def load_document_history(output_path: Path) -> dict:
    history = {
        "by_hash": {},
        "by_source_path": {},
    }

    if not output_path.exists():
        return history

    with open(output_path, "r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                doc = json.loads(raw)
            except json.JSONDecodeError:
                continue

            record = {
                "doc_id": doc.get("doc_id"),
                "version": doc.get("version", 1),
                "content_hash": doc.get("content_hash"),
                "source_path": doc.get("source_path"),
            }
            content_hash = record.get("content_hash")
            source_path = record.get("source_path")
            if content_hash:
                history["by_hash"][content_hash] = record
            if source_path:
                history["by_source_path"][source_path] = record

    return history


def assign_version_and_dedupe(doc: dict, history: dict, in_run_hashes: dict) -> dict:
    content_hash = compute_content_hash(doc)
    doc["content_hash"] = content_hash

    previous = history.get("by_hash", {}).get(content_hash) or in_run_hashes.get(content_hash)
    if previous:
        doc["version"] = previous.get("version", 1)
        doc["is_duplicate"] = True
        doc["duplicate_of"] = previous.get("doc_id")
    else:
        previous_source = history.get("by_source_path", {}).get(str(doc.get("source_path")))
        if previous_source:
            doc["version"] = previous_source.get("version", 1) + 1
        else:
            doc["version"] = 1
        doc["is_duplicate"] = False
        doc["duplicate_of"] = None

    in_run_hashes[content_hash] = {
        "doc_id": doc.get("doc_id"),
        "version": doc.get("version", 1),
        "content_hash": content_hash,
        "source_path": doc.get("source_path"),
    }
    return doc


def enrich_document(doc: dict) -> dict:
    attach_citations(doc)
    enrich_entities(doc)
    return doc