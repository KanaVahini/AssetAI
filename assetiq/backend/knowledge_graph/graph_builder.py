import json
from neo4j_connector import (
    create_plant_node,
    create_equipment_node,
    create_document_node,
    create_person_node,
    create_regulation_node,
    create_failure_node,
    link_nodes
)

def build_graph(input_path="data/processed/cleaned_documents.jsonl"):
    
    with open(input_path) as f:
        documents = [json.loads(line) for line in f]
    
    for doc in documents:
        print(f"Building graph for: {doc['filename']}")
        
        plant_name = doc.get("plant_name", "Unknown Plant")
        
        # 1. Create plant node (MERGE — won't duplicate)
        create_plant_node(plant_name)
        
        # 2. Create document node
        create_document_node(
            doc_id=doc["doc_id"],
            filename=doc["filename"],
            doc_type=doc.get("doc_type", "unknown"),
            plant_name=plant_name
        )
        
        # 3. Link document to plant
        link_nodes(
            from_label="Document",
            from_key="doc_id",
            from_val=doc["doc_id"],
            edge_type="BELONGS_TO",
            to_label="Plant",
            to_key="name",
            to_val=plant_name
        )
        
        # 4. Process each entity
        for entity in doc.get("entities", []):
            etype = entity["type"]
            evalue = entity["value"]
            
            if etype == "equipment_tag":
                create_equipment_node(evalue, plant_name)
                link_nodes("Equipment","tag",evalue,
                           "MENTIONED_IN","Document","doc_id",doc["doc_id"])
                link_nodes("Equipment","tag",evalue,
                           "BELONGS_TO","Plant","name",plant_name)
            
            elif etype == "person":
                create_person_node(evalue)
                link_nodes("Person","name",evalue,
                           "WORKED_ON","Plant","name",plant_name)
            
            elif etype == "regulatory_reference":
                create_regulation_node(evalue)
                link_nodes("Document","doc_id",doc["doc_id"],
                           "COMPLIES_WITH","Regulation","code",evalue)
            
            elif etype == "failure_mode":
                create_failure_node(evalue)
    
    print("\n✅ Knowledge graph built successfully!")
    print("Open Neo4j Browser and run: MATCH (n) RETURN n LIMIT 50")


if __name__ == "__main__":
    build_graph()