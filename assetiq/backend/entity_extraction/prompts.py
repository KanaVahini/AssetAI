EXTRACTION_PROMPT = """
You are an industrial document analyst.
Read the text below and extract these entities:

- equipment_tags: list of equipment IDs 
  (like P-104, V-22, BL-07, Pump P-104)
- dates: list of dates mentioned
- people: list of person names
- failure_modes: list of failures or problems mentioned
- regulations: list of regulation codes 
  (like OISD-137, Factory Act, PESO, IBR)
- actions: list of maintenance actions done

Return ONLY a JSON object. No explanation. No extra text.
Example:
{
  "equipment_tags": ["P-104", "V-22"],
  "dates": ["2024-03-05"],
  "people": ["Rajan Kumar"],
  "failure_modes": ["bearing failure"],
  "regulations": ["OISD-137"],
  "actions": ["bearing replaced", "lubrication done"]
}

TEXT TO ANALYZE:
"""