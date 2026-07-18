import json
import os
import sys
sys.path.append(os.path.dirname(__file__))

from neo4j_connector import (
    create_plant_node,
    create_equipment_node,
    create_document_node,
    create_person_node,
    create_regulation_node,
    create_failure_node,
    create_location_node,
    link_nodes,
    close
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   

INPUT_PATH =os.path.join(
    BASE_DIR,
    "..",
    "..",
    "data",
    "processed",
    "cleaned_documents.jsonl"
)


def build_graph(input_path=INPUT_PATH):

    with open(input_path) as f:
        documents = [json.loads(line) for line in f]

    print(f"Building graph for {len(documents)} documents...\n")

    for doc in documents:
        filename   = doc["filename"]
        doc_id     = doc["doc_id"]
        doc_type   = doc.get("doc_type", "unknown")
        plant_name = doc.get("plant_name", "Unknown Plant")
        entities   = doc.get("entities", [])

        print(f"Processing: {filename}")

        # 1. Create Plant node
        create_plant_node(plant_name)

        # 2. Create Document node
        create_document_node(doc_id, filename, doc_type, plant_name)

        # 3. Link Document → Plant
        link_nodes(
            "Document", "doc_id",  doc_id,
            "BELONGS_TO",
            "Plant",    "name",    plant_name
        )

        # 4. Process each entity
        for entity in entities:
            etype = entity.get("type")
            evalue = entity.get("value", "").strip()

            if not evalue:
                continue

            # Equipment
            if etype == "equipment_tag":
                create_equipment_node(evalue, plant_name)
                link_nodes(
                    "Equipment", "tag",    evalue,
                    "MENTIONED_IN",
                    "Document",  "doc_id", doc_id
                )
                link_nodes(
                    "Equipment", "tag",  evalue,
                    "BELONGS_TO",
                    "Plant",     "name", plant_name
                )

            # Person
            elif etype == "person":
                create_person_node(evalue)
                link_nodes(
                    "Person",   "name",  evalue,
                    "WORKED_ON",
                    "Plant",    "name",  plant_name
                )

            # Regulation
            elif etype == "regulatory_reference":
                create_regulation_node(evalue)
                link_nodes(
                    "Document",   "doc_id", doc_id,
                    "COMPLIES_WITH",
                    "Regulation", "code",   evalue
                )

            # Failure Mode
            elif etype == "failure_mode":
                create_failure_node(evalue)

            # Location
            elif etype == "location":
                create_location_node(evalue)
                link_nodes(
                    "Location", "name",   evalue,
                    "BELONGS_TO",
                    "Plant",    "name",   plant_name
                )

        print(f"  ✅ {len(entities)} entities added to graph")

    close()
    print("\n🎉 Knowledge graph built successfully!")
    print("Open Neo4j Browser and run:")
    print("  MATCH (n) RETURN n LIMIT 100")


if __name__ == "__main__":
    build_graph()


def build_graph_for_doc(doc):
    """Add a single document to existing graph."""
    plant_name = doc.get("plant_name", "Unknown Plant")

    create_plant_node(plant_name)
    create_document_node(
        doc["doc_id"], doc["filename"],
        doc.get("doc_type", "unknown"), plant_name
    )
    link_nodes("Document", "doc_id", doc["doc_id"],
               "BELONGS_TO", "Plant", "name", plant_name)

    for entity in doc.get("entities", []):
        etype  = entity.get("type")
        evalue = entity.get("value", "").strip()
        if not evalue:
            continue

        if etype == "equipment_tag":
            create_equipment_node(evalue, plant_name)
            link_nodes("Equipment", "tag", evalue,
                       "MENTIONED_IN", "Document", "doc_id", doc["doc_id"])
        elif etype == "person":
            create_person_node(evalue)
        elif etype == "regulatory_reference":
            create_regulation_node(evalue)
            link_nodes("Document", "doc_id", doc["doc_id"],
                       "COMPLIES_WITH", "Regulation", "code", evalue)
        elif etype == "failure_mode":
            create_failure_node(evalue)
        elif etype == "location":
            create_location_node(evalue)