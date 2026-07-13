import re

def normalize_equipment_tag(tag):
    """
    Converts any equipment tag variation to standard format.
    Works for any naming convention — no plant-specific rules.
    
    Examples:
    P104    → P-104
    BL07    → BL-07
    PUMP001 → PUMP-001
    HX11    → HX-11
    TK9     → TK-9
    """
    tag = tag.strip().upper()
    
    # Already has correct format (letters-numbers) → keep
    if re.match(r'^[A-Z]+-\d+$', tag):
        return tag
    
    # Letters immediately followed by numbers → insert dash
    match = re.match(r'^([A-Z]+)(\d+)$', tag)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    
    # Already has dash but extra words → extract tag part
    match = re.match(r'.*\b([A-Z]+-\d+)\b.*', tag)
    if match:
        return match.group(1)
    
    # Anything else → return as-is cleaned up
    return tag


def is_noise(entity):
    """
    Filters out things that are not real entities.
    Works for any document — no plant-specific noise list.
    """
    value = entity.get("value", "").strip()
    
    # Too short to be meaningful
    if len(value) < 3:
        return True
    
    # Pure numbers (page numbers, measurements)
    if value.replace(".","").replace("-","").isdigit():
        return True
    
    # Phone numbers
    if re.match(r'^\+?\d[\d\s\-]{7,}$', value):
        return True
    
    # Single letters or common words
    if value.lower() in ["the", "and", "or", "is", "in", 
                          "at", "to", "for", "of", "on"]:
        return True
    
    return False


def fix_entity_type(entity):
    """
    Corrects misclassified entity types.
    Uses patterns — not plant-specific values.
    """
    value = entity["value"].upper()
    
    # Regulatory patterns — any standard/act/regulation
    regulatory_patterns = [
        r'^OISD', r'^ISO\s', r'^PESO', r'^IBR',
        r'ACT\s*\d{4}', r'^ASME', r'^API\s',
        r'^NFPA', r'^BIS\s', r'^IS\s*\d+'
    ]
    for pattern in regulatory_patterns:
        if re.search(pattern, value):
            entity["type"] = "regulatory_reference"
            return entity
    
    # Certificate number patterns
    cert_patterns = [
        r'^IBR-[A-Z]+-\d{4}',
        r'^CALIB-\d{4}',
        r'^CERT-'
    ]
    for pattern in cert_patterns:
        if re.search(pattern, value):
            entity["type"] = "certificate_number"
            return entity
    
    # Equipment tag pattern — letters + dash + numbers
    if re.match(r'^[A-Z]{1,5}-\d{1,4}$', value):
        entity["type"] = "equipment_tag"
        return entity
    
    return entity


def normalize_all_entities(entities):
    """
    Master function — clean all entities in a document.
    """
    cleaned = []
    for entity in entities:
        # Skip noise
        if is_noise(entity):
            continue
        
        # Fix wrong types
        entity = fix_entity_type(entity)
        
        # Normalize equipment tags
        if entity["type"] == "equipment_tag":
            entity["value"] = normalize_equipment_tag(
                entity["value"]
            )
        
        cleaned.append(entity)
    
    return cleaned