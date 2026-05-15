import os
from google import genai
from rapidfuzz import process, fuzz
from staging_transactions.database import get_db_connection

# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = None
if GENAI_API_KEY:
    client = genai.Client(api_key=GENAI_API_KEY)

# Mapping of BudgetBakers friendly names to their internal UUIDs
# TODO: User should populate this with their actual IDs from BudgetBakers
CATEGORY_ID_MAP = {
    "00b4a7be-01a9-44f5-ba87-4745411d819d": "Cargos, tasas tributarias",
    "03209cf1-617c-4aee-a214-e103a014acba": "Casa y jardín",
    "0411de21-d61e-4bf6-a357-aa9b4358b1b3": "Transferencia, retiro",
    "08621677-4423-4129-ae00-7c6f9a4a522f": "Mantenimiento, reparaciones",
    "0acc868d-b275-4c59-8464-a2e905c18460": "Rental income",
    "0be281e6-c079-47a4-8e7b-55710f479ec6": "Caridad, regalos",
    "0c2ff820-e48c-4402-9174-1744c41cc8e9": "Automatic bank statements reading",
    "10fa45d6-0742-437b-af4c-695a1f7bff71": "Cuidado de la salud, médico",
    "1391e334-cc9b-4d74-a4d6-bf68fd856ff3": "Asignación familiar",
    "1c66d924-ea08-4ec6-a65e-4504b5157fd9": "Faltante",
    "20647171-760c-4a48-aa1b-b81437bed97d": "Teléfono, teléfono movil",
    "2225ff31-2c78-4ab6-ae1a-c74e073544d5": "galgerias",
    "225fddb1-5f4d-426f-83ed-40b5fed5af99": "Gadgets salud",
    "23358736-8b60-43a3-b018-cb5608c2a5cc": "Salarios, facturas",
    "263f51c7-23db-4820-a7ce-b372d8c0c7fb": "Comunicaciones, PC",
    "36f47103-4b72-46c7-9e3a-ad30d99bdc42": "Desconocido",
    "3778b86b-0231-4647-abbc-bd6b820ca6fe": "TV, Streaming",
    "44ad9d63-06ca-4db6-af5b-a15aa66059f7": "Papelería, herramientas",
    "473dc28d-4b2e-420d-9bf4-e6a9e2c31222": "Otros",
    "4f3ac2fa-7ac5-4a48-8409-fdf4a8b43b3c": "Comida y Bebida",
    "5aa33e1d-3f15-4b57-9e02-db9d7638df1d": "Salud y belleza",
    "63bb0bc3-0505-4950-aa97-e0e4a2af9020": "Cuotas & donaciones",
}
DEFAULT_CATEGORY_ID = "00b4a7be-01a9-44f5-ba87-4745411d819d"


def get_category_from_db(description: str) -> dict | None:
    """Level 1: Exact match in SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category, budgetbakers_category_id FROM category_mapping WHERE description = ?",
        (description,),
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "category": result["category"],
            "budgetbakers_category_id": result["budgetbakers_category_id"],
        }
    return None


def get_category_fuzzy(description: str) -> dict | None:
    """Level 2: Fuzzy Matching (>90% confidence)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT description, category, budgetbakers_category_id FROM category_mapping"
    )
    mappings = cursor.fetchall()
    conn.close()

    if not mappings:
        return None

    # Map description to a dict of results
    choices = {
        row["description"]: {
            "category": row["category"],
            "id": row["budgetbakers_category_id"],
        }
        for row in mappings
    }

    match = process.extractOne(description, choices.keys(), scorer=fuzz.WRatio)

    if match:
        matched_str, score, _ = match
        if score > 90:
            return {
                "category": choices[matched_str]["category"],
                "budgetbakers_category_id": choices[matched_str]["id"],
            }

    return None


def get_category_gemini(description: str) -> dict:
    """Level 3: Gemini Fallback."""
    if not client:
        cat_name = "Others"
        cat_id = DEFAULT_CATEGORY_ID
    else:
        try:
            # ... prompt omitted for brevity in thought, but keep original logic ...
            prompt = f"""
            You are a financial assistant specialized in expense classification. 
            Your task is to categorize the following description in spanish into EXACTLY ONE category from the allowed list below.

            ALLOWED CATEGORIES:
            {", ".join(f"'{c}'" for c in CATEGORY_ID_MAP.values()) if CATEGORY_ID_MAP else "'Others'"}

            RULES:
            1. Return ONLY the category name. 
            2. Do not include periods, explanations, or extra text.
            3. If the description is ambiguous, choose 'Others'.

            Description: "{description}"
            Category:"""

            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            cat_name = response.text.strip()
            cat_id = [k for k, v in CATEGORY_ID_MAP.items() if v == cat_name][0]
        except Exception as e:
            print(f"Gemini API error: {e}")
            cat_name = "Others"
            cat_id = DEFAULT_CATEGORY_ID

    # Save to DB for future caching
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO category_mapping (description, category, budgetbakers_category_id) VALUES (?, ?, ?)",
        (description, cat_name, cat_id),
    )
    conn.commit()
    conn.close()

    return {"category": cat_name, "budgetbakers_category_id": cat_id}


def determine_category(description: str) -> dict:
    """Main categorizer function implementing the 3 priority levels."""
    # Level 1
    result = get_category_from_db(description)
    if result:
        return result

    # Level 2
    result = get_category_fuzzy(description)
    if result:
        return result

    # Level 3
    return get_category_gemini(description)
