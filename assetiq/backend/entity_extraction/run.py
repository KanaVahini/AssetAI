import json
from extractor import extract_entities
from normalizer import normalize_all

# Load Person 1's output
with open("data/processed/extracted_documents.json") as f:
    documents = json.load(f)

results = []
for doc in documents:
    print(f"Extracting from: {doc['source_file']}")
    
    entities = extract_entities(doc["content"])
    entities = normalize_all(entities)
    
    results.append({
        "doc_id": doc["id"],
        "source_file": doc["source_file"],
        "doc_type": doc["doc_type"],
        "content": doc["content"],
        "entities": entities
    })

# Save output for Person 3
with open("data/processed/entities.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Done! Entities extracted from {len(results)} documents.")