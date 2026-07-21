"""
chroma_store.py
----------------
Vector store using ChromaDB.
- Handles both standard schema pages (text) and mixed_doc pages (prose)
- Uses absolute PROJECT_ROOT path to avoid cwd issues
- Supports build_vector_store(), search(), and add_document()
"""

import json
import os
import sys
sys.path.append(os.path.dirname(__file__))

import chromadb
from chunker import chunk_text
from embedder import embed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# IMPORTANT: anchored to PROJECT_ROOT, not cwd.
# copilot_agent.py calls os.chdir() before importing this module,
# so a cwd-relative path would silently point at a different (empty)
# folder. Absolute path guarantees writers and readers hit the same collection.
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_or_create_collection("assetiq")

INPUT_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "cleaned_documents.jsonl")

# Ensure vector_store output dir exists
output_dir = os.path.join(PROJECT_ROOT, "data", "vector_store")
os.makedirs(output_dir, exist_ok=True)


def _page_text(page):
    """
    Normalizes both page shapes into a plain-text string.

    Standard schema pages (pdf_extractor, ocr_extractor, csv_extractor,
    email_extractor) carry a "text" string.

    mixed_doc_extractor pages have NO "text" key — content lives in
    "prose" (a list of strings). Without this helper, those pages produce
    empty text and get 0 chunks stored.
    """
    if page.get("text"):
        return page["text"]
    if page.get("prose"):
        return " ".join(page["prose"])
    return ""


def build_vector_store(input_path=INPUT_PATH):
    with open(input_path) as f:
        documents = [json.loads(line) for line in f]

    print(f"Building vector store for {len(documents)} documents...\n")

    total_chunks = 0

    for doc in documents:
        filename   = doc["filename"]
        doc_id     = doc["doc_id"]
        plant_name = doc.get("plant_name", "unknown")
        doc_type   = doc.get("doc_type", "unknown")

        # Handles both "text" and "prose" page shapes
        full_text = " ".join([
            _page_text(page)
            for page in doc.get("pages", [])
            if _page_text(page)
        ])

        if not full_text.strip():
            print(f"⚠ Skipping {filename} — no text")
            continue

        chunks = chunk_text(full_text)
        embeddings = embed(chunks)

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_chunk{i}"
            collection.add(
                documents=[chunk],
                embeddings=[emb],
                metadatas=[{
                    "doc_id":      doc_id,
                    "filename":    filename,
                    "doc_type":    doc_type,
                    "plant_name":  plant_name,
                    "chunk_index": i
                }],
                ids=[chunk_id]
            )

        total_chunks += len(chunks)
        print(f"✅ {filename} → {len(chunks)} chunks")

    print(f"\n🎉 Done! {total_chunks} total chunks stored in Chroma")


def search(query, plant_name=None, top_k=5):
    """
    Searches vector store for relevant chunks.
    Optional plant_name filter keeps different plants separate.
    """
    query_embedding = embed([query])

    if plant_name:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where={"plant_name": plant_name}
        )
    else:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )

    return results


def add_document(doc):
    """
    Add a single new document to existing vector store.
    Called by routes.py after auto-upload processing.
    Handles both text and prose page shapes.
    """
    full_text = " ".join([
        _page_text(page)
        for page in doc.get("pages", [])
        if _page_text(page)
    ])

    if not full_text.strip():
        print(f"  ⚠ No text to embed for {doc.get('filename', 'unknown')}")
        return

    chunks = chunk_text(full_text)
    embeddings = embed(chunks)

    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        collection.add(
            documents=[chunk],
            embeddings=[emb],
            metadatas=[{
                "doc_id":      doc["doc_id"],
                "filename":    doc["filename"],
                "doc_type":    doc.get("doc_type", "unknown"),
                "plant_name":  doc.get("plant_name", "unknown"),
                "chunk_index": i
            }],
            ids=[f"{doc['doc_id']}_chunk{i}"]
        )

    print(f"  ✅ Added {len(chunks)} chunks for {doc['filename']}")


if __name__ == "__main__":
    build_vector_store()
