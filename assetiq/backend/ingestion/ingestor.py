import os
import sys
import json
import uuid
from datetime import datetime, timezone

# Fix import path
sys.path.append(os.path.dirname(__file__))
from file_router import route_file

def ingest_folder(folder_path, plant_name="unknown_plant"):
    """
    Generic ingestion — works for ANY plant's documents.
    plant_name is passed in at runtime, never hardcoded.
    """
    documents = []
    
    supported = [".pdf", ".csv", ".xlsx", ".jpg", 
                 ".jpeg", ".png", ".txt"]
    
    for filename in os.listdir(folder_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in supported:
            continue
            
        file_path = os.path.join(folder_path, filename)
        print(f"Processing: {filename}")
        
        try:
            result = route_file(file_path)
            
            if not result:
                print(f"  ⚠ Skipped: {filename}")
                continue
            
            doc = {
                "doc_id": str(uuid.uuid4()),
                "source_path": file_path,
                "filename": filename,
                "doc_type": result.get("doc_type"),
                "plant_name": plant_name,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "pages": result.get("pages", []),
                "entities": result.get("entities", []),
                "metadata": result.get("metadata", {}),
                "is_duplicate": False
            }
            
            documents.append(doc)
            
        except Exception as e:
            print(f"  ❌ Error processing {filename}: {e}")
    
    return documents


def save_output(documents, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        for doc in documents:
            f.write(json.dumps(doc) + "\n")
    print(f"\n✅ {len(documents)} documents saved to {output_path}")


if __name__ == "__main__":
    documents = ingest_folder(
        folder_path="../../data/raw",
        plant_name="Bharat Process Industries"
    )
    save_output(documents, "../../data/processed/ingested_output.jsonl")