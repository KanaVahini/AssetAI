import os
import sys
import json

# ✅ Insert RCA folder FIRST — forces Python to find correct tools.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../rag")))
sys.path.insert(2, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge_graph")))

from groq import Groq
from dotenv import load_dotenv
from tools import build_evidence_context
from prompt import RCA_SYSTEM_PROMPT

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def run(equipment_tag):
    """
    Main RCA function.
    Takes equipment tag → returns structured RCA report.
    """
    print(f"\n🔍 Starting RCA for: {equipment_tag}")

    # Step 1 — Gather all evidence
    print("Step 1: Gathering evidence...")
    evidence_context = build_evidence_context(equipment_tag)

    # Step 2 — Send to LLM for analysis
    print("Step 2: Analyzing evidence with LLM...")

    user_message = f"""
Perform a complete Root Cause Analysis for equipment: {equipment_tag}

Here is all the evidence gathered from documents:

{evidence_context}

Return ONLY the JSON report. No explanation before or after.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": RCA_SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ],
        temperature=0
    )

    raw = response.choices[0].message.content

    # Step 3 — Parse JSON response
    print("Step 3: Parsing report...")

    try:
        raw = raw.replace("```json", "").replace("```", "").strip()
        report = json.loads(raw)

    except Exception as e:
        print(f"  ⚠ JSON parse failed: {e}")
        report = {
            "equipment": equipment_tag,
            "failure_summary": "RCA completed but report formatting failed",
            "raw_analysis": raw,
            "error": str(e)
        }

    print(f"✅ RCA complete for {equipment_tag}")
    return report


if __name__ == "__main__":
    report = run("P-104")
    print("\n" + "="*60)
    print("RCA REPORT")
    print("="*60)
    print(json.dumps(report, indent=2))