"""
startup.py — Master startup script for AssetIQ backend.

This runs automatically when Docker container starts.
It:
1. Checks if data already exists (skip pipeline if yes)
2. If raw documents exist but not processed — runs full pipeline
3. Starts the FastAPI server

This means:
- First run: runs full pipeline (~3 minutes) then starts server
- Subsequent runs: skips pipeline, starts server immediately
"""

import os
import sys
import subprocess
import time

# Always work from project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath("backend"))

print("=" * 60)
print("  AssetIQ — Starting Up")
print("=" * 60)


def files_exist_in(folder, extensions):
    """Check if any files with given extensions exist in folder."""
    if not os.path.exists(folder):
        return False
    for f in os.listdir(folder):
        if any(f.lower().endswith(ext) for ext in extensions):
            return True
    return False


def jsonl_has_content(path):
    """Check if a JSONL file exists and has content."""
    if not os.path.exists(path):
        return False
    with open(path) as f:
        for line in f:
            if line.strip():
                return True
    return False


def chroma_has_content():
    """Check if ChromaDB has any data."""
    chroma_path = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
    return os.path.exists(chroma_path) and len(os.listdir(chroma_path)) > 0


def run_step(name, script_path):
    """Run a pipeline step and show output."""
    print(f"\n🔄 {name}...")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout per step
        )
        if result.returncode == 0:
            print(f"✅ {name} complete")
            if result.stdout.strip():
                # Show last few lines of output
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:
                    print(f"   {line}")
        else:
            print(f"⚠️  {name} had issues (continuing anyway)")
            if result.stderr.strip():
                print(f"   {result.stderr.strip()[-300:]}")
    except subprocess.TimeoutExpired:
        print(f"⚠️  {name} timed out — continuing")
    except Exception as e:
        print(f"⚠️  {name} error: {e} — continuing")


def wait_for_neo4j():
    """Wait for Neo4j to be ready before building graph."""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    print(f"\n⏳ Waiting for Neo4j at {neo4j_uri}...")

    for attempt in range(30):
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(
                    os.getenv("NEO4J_USER", "neo4j"),
                    os.getenv("NEO4J_PASSWORD", "password123")
                )
            )
            driver.verify_connectivity()
            driver.close()
            print("✅ Neo4j is ready")
            return True
        except Exception:
            time.sleep(3)
            print(f"   Attempt {attempt + 1}/30...")

    print("⚠️  Neo4j not available — graph features will be limited")
    return False


# ── DECIDE WHAT TO RUN ─────────────────────────────────────────

raw_docs_exist       = files_exist_in("data/raw", [".pdf", ".csv", ".xlsx", ".jpg", ".jpeg", ".png", ".txt"])
ingested_exists      = jsonl_has_content("data/processed/ingested_output.jsonl")
extracted_exists     = jsonl_has_content("data/processed/extracted_documents.jsonl")
cleaned_exists       = jsonl_has_content("data/processed/cleaned_documents.jsonl")
chroma_exists        = chroma_has_content()

print(f"\n📊 Data Status:")
print(f"   Raw documents:     {'✅' if raw_docs_exist    else '❌'}")
print(f"   Ingested output:   {'✅' if ingested_exists   else '❌'}")
print(f"   Extracted entities:{'✅' if extracted_exists  else '❌'}")
print(f"   Cleaned documents: {'✅' if cleaned_exists    else '❌'}")
print(f"   Vector store:      {'✅' if chroma_exists     else '❌'}")

# Run only the steps that are needed
if not raw_docs_exist:
    print("\n⚠️  No raw documents found in data/raw/")
    print("   Upload documents via the frontend to get started.")
    print("   The server will start and you can upload documents through the UI.")

else:
    print("\n🚀 Running pipeline for any missing steps...")

    if not ingested_exists:
        run_step("Step 1: Ingestion", "backend/ingestion/ingestor.py")
    else:
        print("\n⏭  Step 1: Ingestion — already done, skipping")

    if not extracted_exists:
        run_step("Step 2: Entity Extraction", "backend/entity_extraction/extractor.py")
    else:
        print("⏭  Step 2: Entity Extraction — already done, skipping")

    if not cleaned_exists:
        run_step("Step 3: Cleaning", "backend/entity_extraction/clean_entities.py")
    else:
        print("⏭  Step 3: Cleaning — already done, skipping")

    # Knowledge graph — always try (idempotent with MERGE)
    if cleaned_exists:
        neo4j_ready = wait_for_neo4j()
        if neo4j_ready:
            run_step("Step 4: Knowledge Graph", "backend/knowledge_graph/graph_builder.py")
        else:
            print("⏭  Step 4: Knowledge Graph — Neo4j not available, skipping")

    if not chroma_exists:
        run_step("Step 5: Vector Store", "backend/rag/chroma_store.py")
    else:
        print("⏭  Step 5: Vector Store — already done, skipping")

# ── START SERVER ───────────────────────────────────────────────
print("\n" + "=" * 60)
print("  🚀 Starting AssetIQ API Server...")
print("  📍 http://localhost:8000")
print("  📖 http://localhost:8000/docs")
print("=" * 60 + "\n")

os.execv(sys.executable, [sys.executable, "backend/main.py"])