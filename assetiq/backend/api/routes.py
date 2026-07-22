import os
import sys
import shutil
import threading
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from pydantic import BaseModel



# ── Path setup ────────────────────────────────────────────────
# ── Path setup ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(BASE_DIR, "ingestion"))         # ← FIRST
sys.path.insert(1, os.path.join(BASE_DIR, "entity_extraction"))
sys.path.insert(2, os.path.join(BASE_DIR, "rag"))
sys.path.insert(3, os.path.join(BASE_DIR, "agents/copilot"))
sys.path.insert(4, os.path.join(BASE_DIR, "agents/rca"))
sys.path.insert(5, os.path.join(BASE_DIR, "knowledge_graph"))   # ← LAST


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
    try:
        for mod in ['schema', 'file_router', 'ocr_utils', 'enrichment']:
            if mod in sys.modules:
                del sys.modules[mod]

        print(f"\n🔄 Auto-processing: {os.path.basename(file_path)}")

        from file_router import route_file
        result = route_file(file_path)

        if not result:
            print(f"❌ Could not extract content from {file_path}")
            return

        # ── Normalize result to standard doc format ──────────
        # mixed_doc_extractor returns {doc_type, source_file, pages}
        # pdf_extractor/csv_extractor return full doc with doc_id
        # We need to ensure doc_id always exists
        import uuid
        from datetime import datetime, timezone

        if "doc_id" not in result:
            # mixed_doc_extractor result — add missing fields
            result["doc_id"]      = str(uuid.uuid4())
            result["filename"]    = os.path.basename(file_path)
            result["source_path"] = file_path
            result["plant_name"]  = plant_name
            result["ingested_at"] = datetime.now(timezone.utc).isoformat()
            result["entities"]    = []
            result["is_duplicate"] = False
        else:
            # Standard result — just add plant_name and filename
            result["plant_name"]  = plant_name
            result["filename"]    = os.path.basename(file_path)
            result["is_duplicate"] = False

        doc = result

        # ── Entity Extraction ────────────────────────────────
        from extractor import extract_entities_from_text
        from normalizer import normalize_all_entities

        # Handle both text and prose page shapes
        full_text = " ".join([
            p.get("text", "") or " ".join(p.get("prose", []))
            for p in doc.get("pages", [])
            if p.get("text") or p.get("prose")
        ])

        if full_text.strip():
            raw_entities = extract_entities_from_text(full_text)
            entity_list = []
            for tag in raw_entities.get("equipment_tags", []):
                entity_list.append({"type": "equipment_tag", "value": tag})
            for person in raw_entities.get("people", []):
                entity_list.append({"type": "person", "value": person})
            for failure in raw_entities.get("failure_modes", []):
                entity_list.append({"type": "failure_mode", "value": failure})
            for reg in raw_entities.get("regulations", []):
                entity_list.append({"type": "regulatory_reference", "value": reg})
            for date in raw_entities.get("dates", []):
                entity_list.append({"type": "date", "value": date})
            for loc in raw_entities.get("locations", []):
                entity_list.append({"type": "location", "value": loc})
            doc["entities"] = normalize_all_entities(entity_list)
            print(f"  ✅ Extracted {len(doc['entities'])} entities")
        else:
            print(f"  ⚠ No text found for entity extraction")

        # ── Knowledge Graph ──────────────────────────────────
        try:
            from graph_builder import build_graph_for_doc
            build_graph_for_doc(doc)
            print("  ✅ Added to knowledge graph")
        except Exception as e:
            print(f"  ⚠ Graph update skipped: {e}")

        # ── Vector Store ─────────────────────────────────────
        from chroma_store import add_document
        add_document(doc)
        print("  ✅ Added to vector store")

        # ── Save to cleaned_documents.jsonl ──────────────────
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        output_path = os.path.join(
            project_root, "data/processed/cleaned_documents.jsonl"
        )
        with open(output_path, "a") as f:
            f.write(json.dumps(doc) + "\n")

        print(f"✅ Auto-processing complete: {os.path.basename(file_path)}")

    except Exception as e:
        import traceback
        print(f"❌ Auto-processing failed for {file_path}: {e}")
        print(traceback.format_exc())


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
def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    Upload multiple documents at once.
    Each file is automatically processed through the full pipeline in background.
    """
    uploaded = []
    failed = []

    for file in files:
        try:
            save_path = f"data/raw/{file.filename}"
            with open(save_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            # Each file processed independently in background
            background_tasks.add_task(process_new_document, save_path)
            uploaded.append(file.filename)

        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})

    return {
        "uploaded": uploaded,
        "failed": failed,
        "total_uploaded": len(uploaded),
        "status": "processing",
        "note": f"{len(uploaded)} files uploaded. Processing in background. Ask questions in ~30 seconds per file."
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


@router.get("/equipment/tags")
def get_equipment_tags():
    """Returns list of all equipment tags from Neo4j."""
    try:
        from neo4j_connector import run_query
        results = run_query("MATCH (e:Equipment) RETURN e.tag AS tag ORDER BY e.tag")
        tags = [r["tag"] for r in results if r["tag"]]
        return {"tags": tags}
    except Exception as e:
        return {"tags": [], "error": str(e)}

@router.get("/stats")
def get_stats():
    """Returns basic stats about indexed documents."""
    import json, os
    stats = {"documents": 0, "entities": 0, "chunks": 0}
    try:
        path = "data/processed/cleaned_documents.jsonl"
        if os.path.exists(path):
            with open(path) as f:
                docs = [json.loads(line) for line in f]
            stats["documents"] = len(docs)
            stats["entities"] = sum(len(d.get("entities", [])) for d in docs)
    except Exception:
        pass
    return stats    


# ══════════════════════════════════════════════════════════════
# GRAPH — Knowledge graph data for frontend visualization
# ══════════════════════════════════════════════════════════════

@router.get("/graph")
def get_graph():
    """
    Returns nodes + edges from the knowledge graph for visualization.
    Output: { nodes: list, edges: list }
    """
    try:
        from neo4j_connector import run_query
        results = run_query("""
            MATCH (n)-[r]->(m)
            RETURN n, r, m
            LIMIT 200
        """)

        nodes = {}
        edges = []

        for record in results:
            n, m, r = record["n"], record["m"], record["r"]

            n_id = n.element_id
            m_id = m.element_id

            nodes[n_id] = {
                "id": n_id,
                "label": list(n.labels)[0] if n.labels else "Node",
                "properties": dict(n)
            }
            nodes[m_id] = {
                "id": m_id,
                "label": list(m.labels)[0] if m.labels else "Node",
                "properties": dict(m)
            }
            edges.append({
                "source": n_id,
                "target": m_id,
                "type": r.type
            })

        return {"nodes": list(nodes.values()), "edges": edges}

    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}