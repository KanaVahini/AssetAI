# AssetIQ

AssetIQ is an AI-powered platform that helps industries organize and search plant knowledge. It processes documents such as manuals, P&IDs, inspection reports, maintenance records, and equipment data to provide quick and context-aware answers.

---

## Prerequisites

Make sure you have the following installed:

* Docker Desktop
* A Groq API Key (https://console.groq.com)

---

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd assetiq
```

### 2. Create the environment file

```bash
cp .env.example .env
```

Add your Groq API key to the `.env` file:

```env
GROQ_API_KEY=your_api_key
```


### 3. Start the project

```bash
docker-compose up --build
```

---

## Access

| Service       | URL                        | Description                                                                                                                |
| ------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Frontend      | http://localhost:5173      | Main application interface                                                                                                 |
| API Docs      | http://localhost:8000/docs | Interactive API documentation                                                                                              |
| Neo4j Browser | http://localhost:7474      | View and explore the knowledge graph along with the relationships (graph mappings) generated from the processed documents. |

---

## Documentation

**Technical Documentation (PDF):**

> Add the link here

**Project Presentation (PPT):**

> Add the link here

---

## Team

Built for the **AI for Industrial Knowledge Intelligence Hackathon**.
