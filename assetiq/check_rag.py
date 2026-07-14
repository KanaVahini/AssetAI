import sys
sys.path.append("backend/rag")
from chroma_store import search

# Test query
results = search("Why did Pump P-104 fail?", top_k=3)

print("Top 3 results:\n")
for i, (doc, meta) in enumerate(zip(
    results["documents"][0],
    results["metadatas"][0]
)):
    print(f"Result {i+1}:")
    print(f"  Source: {meta['filename']}")
    print(f"  Text: {doc[:200]}...")
    print()