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

### 4. View the Knowledge Graph

Once all the containers are running:

1. Open the Neo4j Browser:

   ```
   http://localhost:7474
   ```

2. Log in using the following credentials:

   ```text
   Username: neo4j
   Password: password123
   ```

3. After logging in, run the following Cypher query to visualize the generated knowledge graph:

   ```cypher
   MATCH p=(n)-[r]->(m)
   RETURN p;
   ```

   This will display all nodes and relationships extracted from the processed documents.

> **Note:** The knowledge graph will only contain data after documents have been processed through the application. If no documents have been uploaded yet, the graph will be empty.

## Access

| Service       | URL                        | Description                                                                                                             |
| ------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Frontend      | http://localhost:5173      | Main application interface                                                                                              |
| API Docs      | http://localhost:8000/docs | Interactive API documentation                                                                                           |
| Neo4j Browser | http://localhost:7474      | View the generated knowledge graph and explore graph mappings and relationships extracted from the processed documents. |

---

## Documentation

### Technical Documentation

**Technical Documentation PDF:**
https://drive.google.com/file/d/1bbavMC9gF2-SLyNqABpalS7pzlyT008d/view?usp=sharing

### Project Presentation

**Project Presentation Deck:**
https://docs.google.com/presentation/d/1IlCq9q6FNqPda7JIR8igH69LWLBqo5jQ/edit?usp=sharing&ouid=109909952726608552417&rtpof=true&sd=true

The presentation includes:

* Problem Statement
* Proposed Solution
* System Architecture
* Features
* Business Model
* Tech Stack
* Future Scope
* Demo

---

## Team

Built for the **AI for Industrial Knowledge Intelligence Hackathon**.
