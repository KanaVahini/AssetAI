import json
import os
import sys
sys.path.append(os.path.dirname(__file__))

from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT = """
You are an industrial document analyst.
Read the text below and extract these entities.

Return ONLY a JSON object, no explanation, no markdown:
{
  "equipment_tags": [],
  "people": [],
  "failure_modes": [],
  "regulations": [],
  "dates": [],
  "locations": []
}

Rules:
- equipment_tags: physical equipment IDs like P-104, BL-07, V-22, HX-11, WO-2024-001, SOP-CW-003
- people: full names of humans mentioned
- failure_modes: any failure, problem, or defect mentioned
- regulations: any standard, act, or code like OISD-137, Factory Act, PESO, IBR, ISO
- dates: any date mentioned
- locations: any building, room, or area mentioned

TEXT:
"""

def extract_entities_from_text(text):
    # Take first 3000 chars to avoid token limits
    short_text = text[:3000]
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": PROMPT + short_text
            }],
            temperature=0
        )
        
        raw = response.choices[0].message.content
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
        
    except Exception as e:
        print(f"    ⚠ Extraction failed: {e}")
        return {
            "equipment_tags": [],
            "people": [],
            "failure_modes": [],
            "regulations": [],
            "dates": [],
            "locations": []
        }


def run_extraction(
    input_path = os.path.join(
    BASE_DIR,
    "..",
    "..",
    "data",
    "processed",
    "ingested_output.jsonl",
),
   output_path = os.path.join(
    BASE_DIR,
    "..",
    "..",
    "data",
    "processed",
    "extracted_documents.jsonl",
)

):
    with open(input_path) as f:
        documents = [json.loads(line) for line in f]
    
    results = []
    
    for doc in documents:
        print(f"Extracting: {doc['filename']}")
        
        # Combine all page texts
        full_text = " ".join([
            page["text"]
            for page in doc.get("pages", [])
            if page.get("text")
        ])
        
        if not full_text.strip():
            print(f"  ⚠ No text found, skipping")
            results.append(doc)
            continue
        
        # Extract entities using Groq
        entities = extract_entities_from_text(full_text)
        
        # Convert to standard format
        doc["entities"] = []
        
        for tag in entities.get("equipment_tags", []):
            doc["entities"].append({"type": "equipment_tag", "value": tag})
        
        for person in entities.get("people", []):
            doc["entities"].append({"type": "person", "value": person})
        
        for failure in entities.get("failure_modes", []):
            doc["entities"].append({"type": "failure_mode", "value": failure})
        
        for reg in entities.get("regulations", []):
            doc["entities"].append({"type": "regulatory_reference", "value": reg})
        
        for date in entities.get("dates", []):
            doc["entities"].append({"type": "date", "value": date})
        
        for loc in entities.get("locations", []):
            doc["entities"].append({"type": "location", "value": loc})
        
        print(f"  ✅ {len(doc['entities'])} entities found")
        results.append(doc)
    
    # Save output
    with open(output_path, "w") as f:
        for doc in results:
            f.write(json.dumps(doc) + "\n")
    
    print(f"\n✅ Done! Saved to {output_path}")


if __name__ == "__main__":
    run_extraction()