import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
USER     = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

driver = GraphDatabase.driver(
    URI,
    auth=(USER, PASSWORD),
    encrypted=False
)


def run_query(query, params={}):
    with driver.session() as session:
        result = session.run(query, params)
        return list(result)


def close():
    driver.close()


# ─── Node creators (MERGE = won't duplicate) ──────────────

def create_plant_node(name):
    run_query("""
        MERGE (p:Plant {name: $name})
        RETURN p
    """, {"name": name})


def create_equipment_node(tag, plant_name):
    run_query("""
        MERGE (e:Equipment {tag: $tag})
        SET e.plant_name = $plant_name
        RETURN e
    """, {"tag": tag, "plant_name": plant_name})


def create_document_node(doc_id, filename, doc_type, plant_name):
    run_query("""
        MERGE (d:Document {doc_id: $doc_id})
        SET d.filename   = $filename,
            d.doc_type   = $doc_type,
            d.plant_name = $plant_name
        RETURN d
    """, {
        "doc_id":     doc_id,
        "filename":   filename,
        "doc_type":   doc_type,
        "plant_name": plant_name
    })


def create_person_node(name):
    run_query("""
        MERGE (p:Person {name: $name})
        RETURN p
    """, {"name": name})


def create_regulation_node(code):
    run_query("""
        MERGE (r:Regulation {code: $code})
        RETURN r
    """, {"code": code})


def create_failure_node(name):
    run_query("""
        MERGE (f:FailureMode {name: $name})
        RETURN f
    """, {"name": name})


def create_location_node(name):
    run_query("""
        MERGE (l:Location {name: $name})
        RETURN l
    """, {"name": name})


# ─── Edge creators ─────────────────────────────────────────

def link_nodes(
    from_label, from_key, from_val,
    edge_type,
    to_label, to_key, to_val
):
    query = f"""
        MATCH (a:{from_label} {{{from_key}: $from_val}})
        MATCH (b:{to_label}   {{{to_key}:   $to_val}})
        MERGE (a)-[:{edge_type}]->(b)
    """
    run_query(query, {
        "from_val": from_val,
        "to_val":   to_val
    })