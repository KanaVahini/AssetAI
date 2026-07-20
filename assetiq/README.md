# AssetIQ — AI-Powered Industrial Knowledge Intelligence

> Unified AI brain for industrial plant knowledge — making every document, 
> maintenance record, and operational insight instantly queryable.

---

## 🚀 One Command Setup (Docker)

**Prerequisites — install these once:**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 
- A free Groq API key from [console.groq.com](https://console.groq.com)

**Step 1 — Clone the repo:**
```bash
git clone <your-repo-url>
cd assetiq
```

**Step 2 — Create your .env file:**
```bash
cp .env.example .env
```
Open `.env` and add your Groq API key:
```
GROQ_API_KEY=your_actual_key_here
```

**Step 3 — Add your documents:**
```
Put your plant documents (PDFs, CSVs, images) into:
assetiq/data/raw/
```

**Step 4 — Start everything:**
```bash
docker-compose up --build
```

That's it. Open your browser:
- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs
- **Neo4j Browser:** http://localhost:7474

---

## 🔄 What Happens Automatically

When you run `docker-compose up`:

```
1. Neo4j database starts
2. Backend starts and runs the full pipeline:
   → Reads all documents from data/raw/
   → Extracts text (PDF, CSV, images via OCR)
   → Extracts entities using Groq AI
   → Builds knowledge graph in Neo4j
   → Creates vector embeddings in ChromaDB
3. Frontend builds and serves on port 5173
4. API server starts on port 8000
```

On subsequent runs, the pipeline is skipped (data already exists).
Server starts in seconds.

---

## 📁 Adding New Documents

**Option 1 — Through the UI:**
Go to http://localhost:5173/upload and upload any file.
It automatically processes in the background (~30 seconds).

**Option 2 — Directly:**
Drop files into `data/raw/` and restart:
```bash
docker-compose restart backend
```

**Supported file types:**
- PDF (digital and scanned)
- CSV / Excel
- Images (JPEG, PNG) — OCR applied
- Text files (.txt)

---

## 🎯 Features

| Feature | URL | Description |
|---------|-----|-------------|
| Copilot Chat | /copilot | Ask anything about your plant documents |
| RCA Analysis | /rca | Root cause analysis for equipment failures |
| Safety Dashboard | /safety | Safety status and compliance report |
| Document Summary | /summary | Overview of all indexed documents |
| File Upload | /upload | Upload new documents to the system |

---

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /ask | Copilot Q&A |
| POST | /rca | Root Cause Analysis |
| GET | /safety | Full safety report |
| POST | /safety/check | Equipment safety check |
| GET | /summary | Document summary |
| POST | /summary/document | Topic summary |
| POST | /upload | Upload document |
| GET | /health | Health check |

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js, Tailwind CSS, Axios |
| Backend | FastAPI, Python 3.12 |
| AI/LLM | Groq API (Llama 3.3 70B) |
| Vector DB | ChromaDB |
| Graph DB | Neo4j 5 |
| Embeddings | BAAI/bge-small-en (local) |
| OCR | Tesseract |
| Container | Docker, Docker Compose |

---

## 🔧 Running Without Docker (Development)

**Backend:**
```bash
pip install -r requirements.txt
python startup.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Neo4j:** Install [Neo4j Desktop](https://neo4j.com/download/) 
and start a database with password `password123`.

---

## 📊 Demo Queries

Try these in the Copilot:

1. `"What is the emergency shutdown procedure for Pump P-104?"`
2. `"What lubrication interval does the OEM recommend for KDS-450 pumps?"`
3. `"Why did Pump P-104 fail in March 2024 and could it have been predicted?"`

Try this in RCA:
- Equipment Tag: `P-104`

---

## 🔑 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| GROQ_API_KEY | Groq API key (required) | — |
| NEO4J_URI | Neo4j connection URI | bolt://neo4j:7687 |
| NEO4J_USER | Neo4j username | neo4j |
| NEO4J_PASSWORD | Neo4j password | password123 |
| CHROMA_DB_PATH | ChromaDB storage path | data/chroma_db |

---

## 👥 Team

Built for the AI for Industrial Knowledge Intelligence Hackathon.