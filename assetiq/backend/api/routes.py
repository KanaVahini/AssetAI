import os
import sys
import shutil
import threading
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────
sys.path.append(os.path.abspath("backend/agents/copilot"))
sys.path.append(os.path.abspath("backend/agents/rca"))
sys.path.append(os.path.abspath("backend/rag"))
sys.path.append(os.path.abspath("backend/ingestion"))
sys.path.append(os.path.abspath("backend/entity_extraction"))
sys.path.append(os.path.abspath("backend/knowledge_graph"))

from agents.copilot import copilot_agent
from agents.rca import rca_agent

router = APIRouter()


# ── Request Models ─────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    plant_name: Optional[str] = None


class RCARequest(BaseModel):
    equipment_tag: str


class SafetyCheckRequest(BaseModel):
    equipment_tag: str


# ══════════════════════════════════════════════════════════════
# BACKGROUND PROCESSING — runs after file upload
# ══════════════════════════════════════════════════════════════
def process_new_document(file_path: str, plant_name: str = "Bharat Process Industries"):
    """
    Runs in background thread after a file is uploaded.
    Processes the file through the full pipeline automatically.
    """
    try:
        print(f"\n🔄 Auto-processing: {os.path.basename(file_path)}")

        # ── Step 1: Ingest ──────────────────────────────────
        from file_router import route_file
        result = route_file(file_path)

        if not result:
            print(f"❌ Could not extract content from {file_path}")
            return

        doc = {
            "doc_id":      str(uuid.uuid4()),
            "source_path": file_path,
            "filename":    os.path.basename(file_path),
            "doc_type":    result.get("doc_type"),
            "plant_name":  plant_name,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "pages":       result.get("pages", []),
            "entities":    result.get("entities", []),
            "metadata":    result.get("metadata", {}),
            "is_duplicate": False
        }

        # ── Step 2: Entity Extraction ───────────────────────
        from extractor import extract_entities_from_text
        from normalizer import normalize_all_entities

        full_text = " ".join([
            p["text"] for p in doc["pages"] if p.get("text")
        ])

        if full_text.strip():
            raw_entities = extract_entities_from_text(full_text)
            doc["entities"] = normalize_all_entities(raw_entities)
            print(f"  ✅ Extracted {len(doc['entities'])} entities")

        # ── Step 3: Knowledge Graph ─────────────────────────
        try:
            from graph_builder import build_graph_for_doc
            build_graph_for_doc(doc)
            print("  ✅ Added to knowledge graph")
        except Exception as e:
            print(f"  ⚠ Graph update skipped: {e}")

        # ── Step 4: Vector Store ────────────────────────────
        from chroma_store import add_document
        add_document(doc)
        print("  ✅ Added to vector store")

        # ── Step 5: Save to cleaned_documents.jsonl ─────────
        output_path = "data/processed/cleaned_documents.jsonl"
        with open(output_path, "a") as f:
            f.write(json.dumps(doc) + "\n")

        print(f"✅ Auto-processing complete: {os.path.basename(file_path)}")

    except Exception as e:
        print(f"❌ Auto-processing failed for {file_path}: {e}")


# ══════════════════════════════════════════════════════════════
# BASIC ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/")
def home():
    return {"status": "AssetIQ is running", "version": "1.0"}


@router.get("/health")
def health_check():
    return {"status": "healthy"}


# ══════════════════════════════════════════════════════════════
# COPILOT — Q&A
# ══════════════════════════════════════════════════════════════

@router.post("/ask")
def ask_question(request: QueryRequest):
    """
    Copilot Q&A — ask anything about indexed documents.
    Input:  { question: string, plant_name: string (optional) }
    Output: { answer: string, sources: list, chunks_used: int }
    """
    result = copilot_agent.run(
        user_query=request.question,
        plant_name=request.plant_name
    )
    return result


# ══════════════════════════════════════════════════════════════
# RCA AGENT — Root Cause Analysis
# ══════════════════════════════════════════════════════════════

@router.post("/rca")
def run_rca(request: RCARequest):
    """
    RCA Agent — full failure investigation report.
    Input:  { equipment_tag: string }
    Output: Full RCA JSON report with 12 fields
    """
    report = rca_agent.run(request.equipment_tag)
    return report


# ══════════════════════════════════════════════════════════════
# UPLOAD — with auto-pipeline
# ══════════════════════════════════════════════════════════════

@router.post("/upload")
def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a new document.
    Automatically processes it through the full pipeline in background.
    User can ask questions about it after ~30 seconds.
    """
    save_path = f"data/raw/{file.filename}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run full pipeline in background — don't make user wait
    background_tasks.add_task(process_new_document, save_path)

    return {
        "message":    f"Uploaded {file.filename} successfully",
        "status":     "processing",
        "note":       "Document is being processed. You can ask questions about it in ~30 seconds.",
        "filename":   file.filename
    }


# ══════════════════════════════════════════════════════════════
# SAFETY — Safety analysis endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/safety")
def get_safety_report():
    """
    Analyses all documents and returns a full safety status report.
    Covers: overdue items, non-compliances, near-miss patterns, 
    equipment at risk, regulatory violations, urgent actions.
    Output: { safety_report: string, sources: list, generated_at: string }
    """
    safety_question = """
    Analyze all documents and provide a detailed safety status report covering:

    1. OVERDUE COMPLIANCE ITEMS — any inspections or repairs past their deadline with dates
    2. OPEN NON-COMPLIANCES — items flagged as non-compliant in inspection reports
    3. NEAR MISS PATTERNS — recurring near-miss incidents and what equipment is affected
    4. EQUIPMENT AT RISK — equipment showing warning signs based on maintenance records
    5. REGULATORY VIOLATIONS — any Factory Act, PESO, OISD, IBR violations found
    6. IMMEDIATE ACTIONS REQUIRED — things needing urgent attention today

    Be specific — include equipment tags, dates, deadlines, and responsible persons.
    """

    result = copilot_agent.run(user_query=safety_question)

    return {
        "safety_report": result["answer"],
        "sources":       result["sources"],
        "generated_at":  datetime.now().isoformat()
    }


@router.post("/safety/check")
def check_equipment_safety(request: SafetyCheckRequest):
    """
    Check safety status of a specific piece of equipment.
    Input:  { equipment_tag: string }
    Output: { answer: string, sources: list }
    """
    safety_question = f"""
    For equipment {request.equipment_tag}, provide a safety status report covering:

    1. Current safety and operational status
    2. Last inspection date and what was found
    3. Any open safety issues or non-compliances
    4. Upcoming inspection or maintenance deadlines
    5. Any safety-related incidents or near-misses involving this equipment
    6. Specific safety recommendations

    Be specific with dates, temperatures, measurements, and names.
    """

    result = copilot_agent.run(user_query=safety_question)
    return result


# ══════════════════════════════════════════════════════════════
# SUMMARY — Document summary endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/summary")
def get_full_summary():
    """
    Generates a comprehensive summary of ALL indexed documents.
    Covers: equipment list, recent incidents, maintenance done,
    compliance status, key people, pending actions.
    Output: { answer: string, sources: list }
    """
    summary_question = """
    Provide a comprehensive structured summary of all indexed documents covering:

    1. EQUIPMENT INVENTORY — list all equipment mentioned with their status
    2. RECENT INCIDENTS — any failures, breakdowns, or incidents that occurred
    3. MAINTENANCE ACTIVITIES — what maintenance work was done recently
    4. COMPLIANCE STATUS — current regulatory compliance status
    5. KEY PERSONNEL — who is responsible for what
    6. PENDING ACTION ITEMS — what still needs to be done
    7. CRITICAL FINDINGS — the most important things to know

    Be specific and include dates, equipment tags, and names.
    """

    result = copilot_agent.run(user_query=summary_question)
    return result


@router.post("/summary/document")
def summarize_topic(request: QueryRequest):
    """
    Generates a focused summary on a specific topic or equipment.
    Input:  { question: string } — the topic to summarize
    Output: { answer: string, sources: list }
    """
    summary_question = f"""
    Provide a detailed structured summary specifically about: {request.question}

    Cover:
    1. Overview and current status
    2. Key events and timeline
    3. Important technical details
    4. Issues found and actions taken
    5. What needs attention next

    Be specific with dates, measurements, and document references.
    """

    result = copilot_agent.run(
        user_query=summary_question,
        plant_name=request.plant_name
    )
    return result