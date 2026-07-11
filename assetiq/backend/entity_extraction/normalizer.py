# This fixes "P104" "Pump104" "P-104" → all become "P-104"

EQUIPMENT_MAP = {
    "p104": "P-104",
    "pump104": "P-104",
    "pump-104": "P-104",
    "pump p-104": "P-104",
    "cw pump p-104": "P-104",
    "p105": "P-105",
    "pump105": "P-105",
    "v22": "V-22",
    "v23": "V-23",
    "bl07": "BL-07",
    "bl-07": "BL-07",
    "boiler07": "BL-07",
    "hx11": "HX-11",
    "hx12": "HX-12",
    "mv31": "MV-31",
    "ct01": "CT-01",
    "ct-01": "CT-01",
}

def normalize_equipment(tag):
    return EQUIPMENT_MAP.get(tag.lower().strip(), tag)

def normalize_all(entities):
    entities["equipment_tags"] = [
        normalize_equipment(t) 
        for t in entities["equipment_tags"]
    ]
    return entities