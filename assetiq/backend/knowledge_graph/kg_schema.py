# Defines what nodes and edges exist in the knowledge graph
# Generic — works for any plant

NODE_TYPES = {
    "Plant": {
        "required": ["name"],
        "optional": ["location", "industry", "description"]
    },
    "Equipment": {
        "required": ["tag"],
        "optional": ["name", "type", "location",
                     "manufacturer", "model", "status"]
    },
    "Document": {
        "required": ["doc_id", "filename"],
        "optional": ["doc_type", "plant_name", "ingested_at"]
    },
    "Person": {
        "required": ["name"],
        "optional": ["role", "department"]
    },
    "Regulation": {
        "required": ["code"],
        "optional": ["full_name", "issuing_body"]
    },
    "FailureMode": {
        "required": ["name"],
        "optional": ["category", "severity"]
    },
    "Location": {
        "required": ["name"],
        "optional": ["plant", "building", "floor"]
    }
}

EDGE_TYPES = [
    "BELONGS_TO",       # Equipment/Document → Plant
    "MENTIONED_IN",     # Equipment → Document
    "MAINTAINED_BY",    # Equipment → Person
    "HAD_FAILURE",      # Equipment → FailureMode
    "COMPLIES_WITH",    # Document → Regulation
    "WORKED_ON",        # Person → Equipment
    "REFERENCES",       # Document → Document
    "LOCATED_IN",       # Equipment → Location
]