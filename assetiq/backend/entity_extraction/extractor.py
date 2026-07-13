import json
import os
from groq import Groq
from dotenv import load_dotenv
from backend.entity_extraction.prompts import EXTRACTION_PROMPT

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_entities(text):
    # Don't send huge texts — take first 2000 chars
    short_text = text[:2000]
    
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT + short_text
        }],
        temperature=0
    )
    
    raw = response.choices[0].message.content
    
    # Clean and parse JSON
    try:
        raw = raw.replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"JSON parsing failed: {e}")
        print(f"Raw response was: {raw}")
        return {
            "equipment_tags": [],
            "dates": [],
            "people": [],
            "failure_modes": [],
            "regulations": [],
            "actions": []
        }