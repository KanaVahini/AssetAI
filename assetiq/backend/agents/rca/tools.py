import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../rag"))
sys.path.append(os.path.join(os.path.dirname(__file__), "../../knowledge_graph"))

from chroma_store import search
from neo4j_connector import run_query


def get_equipment_documents(equipment_tag):
    """
    Gets all documents mentioning this equipment from Neo4j.
    """
    try:
        results = run_query("""
            MATCH (e:Equipment {tag: $tag})-[:MENTIONED_IN]->(d:Document)
            RETURN d.filename AS filename, d.doc_type AS doc_type
        """, {"tag": equipment_tag})

        docs = [
            {
                "filename": r["filename"],
                "doc_type": r["doc_type"]
            }
            for r in results
        ]
        return docs

    except Exception as e:
        print(f"  Neo4j error: {e}")
        return []


def get_failure_history(equipment_tag):
    """
    Gets all failure modes linked to this equipment from Neo4j.
    """
    try:
        results = run_query("""
            MATCH (e:Equipment {tag: $tag})-[:HAD_FAILURE]->(f:FailureMode)
            RETURN f.name AS failure
        """, {"tag": equipment_tag})

        return [r["failure"] for r in results]

    except Exception as e:
        print(f"  Neo4j error: {e}")
        return []


def get_related_people(equipment_tag):
    """
    Gets all people who worked on this equipment.
    """
    try:
        results = run_query("""
            MATCH (p:Person)-[:WORKED_ON]->(e:Equipment {tag: $tag})
            RETURN p.name AS person
        """, {"tag": equipment_tag})

        return [r["person"] for r in results]

    except Exception as e:
        print(f"  Neo4j error: {e}")
        return []


def get_relevant_chunks(query, top_k=8):
    """
    Gets most relevant document chunks from Chroma vector DB.
    """
    try:
        results = search(query, top_k=top_k)

        chunks = []
        for doc, meta in zip(
            results["documents"][0],
            results["metadatas"][0]
        ):
            chunks.append({
                "text": doc,
                "source": meta["filename"]
            })

        return chunks

    except Exception as e:
        print(f"  Chroma error: {e}")
        return []


def build_evidence_context(equipment_tag):
    """
    Master function — gathers ALL evidence for RCA.
    Combines Neo4j graph data + Chroma vector search.
    """
    print(f"  Gathering evidence for: {equipment_tag}")

    # 1. Graph data
    linked_docs    = get_equipment_documents(equipment_tag)
    failure_history = get_failure_history(equipment_tag)
    people         = get_related_people(equipment_tag)

    # 2. Vector search — multiple targeted queries
    queries = [
        f"{equipment_tag} failure root cause",
        f"{equipment_tag} maintenance history lubrication",
        f"{equipment_tag} bearing temperature vibration",
        f"{equipment_tag} OEM specification interval",
        f"{equipment_tag} incident report corrective action"
    ]

    all_chunks = []
    seen_texts = set()

    for query in queries:
        chunks = get_relevant_chunks(query, top_k=3)
        for chunk in chunks:
            # Deduplicate
            if chunk["text"] not in seen_texts:
                seen_texts.add(chunk["text"])
                all_chunks.append(chunk)

    # 3. Build formatted context string
    context = f"""
EQUIPMENT UNDER INVESTIGATION: {equipment_tag}

DOCUMENTS MENTIONING THIS EQUIPMENT:
{chr(10).join([f"- {d['filename']} ({d['doc_type']})" 
               for d in linked_docs]) or "None found"}

KNOWN FAILURE HISTORY:
{chr(10).join([f"- {f}" for f in failure_history]) or "None found"}

PEOPLE INVOLVED:
{chr(10).join([f"- {p}" for p in people]) or "None found"}

RELEVANT DOCUMENT EVIDENCE:
"""

    for i, chunk in enumerate(all_chunks, 1):
        context += f"""
[Evidence {i} — Source: {chunk['source']}]
{chunk['text']}
"""

    return context