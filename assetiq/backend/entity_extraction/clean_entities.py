"""
clean_entities.py
------------------
Cleans and normalizes extracted entities from extracted_documents.jsonl.
Uses absolute PROJECT_ROOT paths to avoid cwd issues.
"""

import os
import json
from normalizer import normalize_all_entities

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))


def clean_all_documents(
    input_path=os.path.join(PROJECT_ROOT, "data", "processed", "extracted_documents.jsonl"),
    output_path=os.path.join(PROJECT_ROOT, "data", "processed", "cleaned_documents.jsonl")
):
    cleaned_docs = []
    skipped = 0

    with open(input_path) as f:
        for line in f:
            doc = json.loads(line.strip())

            # Skip duplicates
            if doc.get("is_duplicate"):
                skipped += 1
                continue

            # Clean entities using generic normalizer
            doc["entities"] = normalize_all_entities(
                doc.get("entities", [])
            )

            cleaned_docs.append(doc)

    # Save cleaned output
    with open(output_path, "w") as f:
        for doc in cleaned_docs:
            f.write(json.dumps(doc) + "\n")

    print(f"✅ Cleaned {len(cleaned_docs)} documents")
    print(f"⏭ Skipped {skipped} duplicates")
    print(f"📁 Saved to: {output_path}")

    return cleaned_docs


if __name__ == "__main__":
    clean_all_documents()
