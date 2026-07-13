"""
Orchestrator. Run this file directly:

    python -m ingestion.pipeline sample_docs/ output/ingested_output.jsonl

Walks a file or folder, routes each file to its handler via file_router,
and writes one normalized JSON document per line to the output file.
A single bad/corrupt file is logged and skipped — it never kills the batch.
"""

import sys
import json
from pathlib import Path

from file_router import get_handler, supported_extensions
from enrichment import (
    assign_version_and_dedupe,
    enrich_document,
    load_document_history,
)


def ingest_path(path: Path):
    ext = path.suffix.lower()
    handler = get_handler(ext)
    if not handler:
        print(f"[skip] unsupported file type: {path.name}")
        return None

    print(f"[ingest] {path.name} -> {handler.__name__}")
    try:
        return handler(path)
    except Exception as e:
        print(f"[error] failed on {path.name}: {e}")
        return None


def run(input_path: str, output_path: str = "output/ingested_output.jsonl"):
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    history = load_document_history(output_path)
    in_run_hashes = {}

    if input_path.is_file():
        targets = [input_path]
    else:
        targets = sorted(
            p for p in input_path.rglob("*")
            if p.is_file() and p.suffix.lower() in supported_extensions()
        )

    success_count = 0
    with open(output_path, "w") as f:
        for p in targets:
            doc = ingest_path(p)
            if doc:
                doc = enrich_document(doc)
                doc = assign_version_and_dedupe(doc, history, in_run_hashes)
                f.write(json.dumps(doc) + "\n")
                success_count += 1

    print(f"\nDone. {success_count}/{len(targets)} files ingested -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ingestion.pipeline <file_or_folder> [output_path]")
        sys.exit(1)

    in_arg = sys.argv[1]
    out_arg = sys.argv[2] if len(sys.argv) > 2 else "output/ingested_output.jsonl"
    run(in_arg, out_arg)
