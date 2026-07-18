import json
import os
import sys
sys.path.append(os.path.dirname(__file__))

import chromadb
from chunker import chunk_text
from embedder import embed

# Persistent storage — survives restarts
client = chromadb.PersistentClient(path="data/chroma_db")
collection = client.get_or_create_collection("assetiq")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

INPUT_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed",
    "cleaned_documents.jsonl"
)
output_dir = os.path.join(PROJECT_ROOT, "data", "vector_store")
os.makedirs(output_dir, exist_ok=True)

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

        # Combine all pages into one text
        full_text = " ".join([
            page["text"]
            for page in doc.get("pages", [])
            if page.get("text")
        ])

        if not full_text.strip():
            print(f"⚠ Skipping {filename} — no text")
            continue

        # Chunk the text
        chunks = chunk_text(full_text)

        # Embed all chunks
        embeddings = embed(chunks)

        # Store in Chroma
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_chunk{i}"

            collection.add(
                documents=[chunk],
                embeddings=[emb],
                metadatas=[{
                    "doc_id":     doc_id,
                    "filename":   filename,
                    "doc_type":   doc_type,
                    "plant_name": plant_name,
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
    Optional plant filter keeps different plants separate.
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


if __name__ == "__main__":
    build_vector_store()


def add_document(doc):
    """Add a single new document to existing vector store."""
    full_text = " ".join([
        page["text"]
        for page in doc.get("pages", [])
        if page.get("text")
    ])

    if not full_text.strip():
        return

    chunks = chunk_text(full_text)
    embeddings = embed(chunks)

    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        collection.add(
            documents=[chunk],
            embeddings=[emb],
            metadatas=[{
                "doc_id": doc["doc_id"],
                "filename": doc["filename"],
                "doc_type": doc.get("doc_type", "unknown"),
                "plant_name": doc.get("plant_name", "unknown"),
                "chunk_index": i
            }],
            ids=[f"{doc['doc_id']}_chunk{i}"]
        )
    print(f"  Added {len(chunks)} chunks for {doc['filename']}")