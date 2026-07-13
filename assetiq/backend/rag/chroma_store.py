import json
import chromadb
from chunker import chunk_text
from embedder import embed

client = chromadb.PersistentClient(path="data/chroma_db")
collection = client.get_or_create_collection("assetiq")

def build_vector_store(
    input_path="data/processed/cleaned_documents.jsonl"
):
    with open(input_path) as f:
        documents = [json.loads(line) for line in f]
    
    for doc in documents:
        # Combine all pages into one text
        full_text = " ".join([
            page["text"] 
            for page in doc.get("pages", [])
            if page.get("text")
        ])
        
        if not full_text.strip():
            continue
        
        chunks = chunk_text(full_text)
        embeddings = embed(chunks)
        
        for i, (chunk, emb) in enumerate(
            zip(chunks, embeddings)
        ):
            collection.add(
                documents=[chunk],
                embeddings=[emb],
                metadatas=[{
                    "doc_id": doc["doc_id"],
                    "filename": doc["filename"],
                    "doc_type": doc.get("doc_type","unknown"),
                    "plant_name": doc.get("plant_name","unknown"),
                    "chunk_index": i
                }],
                ids=[f"{doc['doc_id']}_chunk{i}"]
            )
    
    print("✅ Vector store built!")


def search(query, plant_name=None, top_k=5):
    """
    Search documents.
    plant_name filter ensures different plants don't mix.
    """
    query_embedding = embed([query])
    
    # If plant specified — search only that plant
    if plant_name:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where={"plant_name": plant_name}
        )
    else:
        # Search all plants
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
    
    return results