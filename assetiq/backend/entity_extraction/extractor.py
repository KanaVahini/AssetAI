import json
from groq import Groq
from prompts import EXTRACTION_PROMPT

client = Groq(api_key="your_groq_key_here")

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
        # Remove any markdown if present
        raw = raw.replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except:
        # If parsing fails return empty
        return {
            "equipment_tags": [],
            "dates": [],
            "people": [],
            "failure_modes": [],
            "regulations": [],
            "actions": []
        }