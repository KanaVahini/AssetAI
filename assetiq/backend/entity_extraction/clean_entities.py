import json
from normalizer import normalize_all_entities

def clean_all_documents(input_path, output_path):
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
    clean_all_documents(
        input_path="data/processed/ingested_output.jsonl",
        output_path="data/processed/cleaned_documents.jsonl"
    )