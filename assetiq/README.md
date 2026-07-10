# AssetIQ

One-line description: AssetIQ is a system for ingesting assets, extracting entities, building a knowledge graph, and providing RAG-enabled assistance.

Setup
-
1. Create a Python virtual environment and activate it.
2. Install requirements: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in keys.

Running
-
- Start the backend: `python -m backend.main` or `uvicorn backend.main:app --reload --port 8000`.
- Run the pipeline: `python pipeline.py`.
