import os
import sys
import subprocess

# Always run from project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath("backend"))

print("=" * 60)
print("  AssetIQ — Starting Full Pipeline")
print("=" * 60)

def run_step(name, module_path):
    print(f"\n🔄 {name}...")
    try:
        result = subprocess.run(
            [sys.executable, module_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ {name} complete")
            if result.stdout:
                print(result.stdout[-500:])  # last 500 chars
        else:
            print(f"❌ {name} failed")
            print(result.stderr[-500:])
    except Exception as e:
        print(f"❌ {name} error: {e}")

# Step 1 — Ingest raw documents
run_step("Step 1: Ingestion", "backend/ingestion/ingestor.py")

# Step 2 — Extract entities
run_step("Step 2: Entity Extraction", "backend/entity_extraction/extractor.py")

# Step 3 — Clean entities
run_step("Step 3: Cleaning", "backend/entity_extraction/clean_entities.py")

# Step 4 — Build knowledge graph
run_step("Step 4: Knowledge Graph", "backend/knowledge_graph/graph_builder.py")

# Step 5 — Build vector store
run_step("Step 5: Vector Store", "backend/rag/chroma_store.py")

print("\n" + "=" * 60)
print("  ✅ Pipeline Complete! Starting API server...")
print("=" * 60 + "\n")

# Step 6 — Start FastAPI server
os.system(f"{sys.executable} backend/main.py")

