import os
import json
from google import genai
from rapidfuzz import process, fuzz
from staging_transactions.database import get_db_connection

# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = None
if GENAI_API_KEY:
    client = genai.Client(api_key=GENAI_API_KEY)

# Load category and account maps from JSON files
# Config files are now located in the root 'config/' folder
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORY_JSON_PATH = os.path.join(ROOT_DIR, "config", "category_map.json")
ACCOUNTS_JSON_PATH = os.path.join(ROOT_DIR, "config", "accounts_map.json")

try:
    with open(CATEGORY_JSON_PATH, "r", encoding="utf-8") as f:
        CATEGORY_ID_MAP = json.load(f)
except Exception as e:
    print(f"Error loading category_map.json: {e}")
    CATEGORY_ID_MAP = {}

try:
    with open(ACCOUNTS_JSON_PATH, "r", encoding="utf-8") as f:
        ACCOUNTS_MAP = json.load(f)
except Exception as e:
    print(f"Error loading accounts_map.json: {e}")
    ACCOUNTS_MAP = {}

DEFAULT_CATEGORY_ID = "00b4a7be-01a9-44f5-ba87-4745411d819d"
DEFAULT_ACCOUNT_ID = "55e461be-cf71-49a1-9b1c-2c436f3ba29c"


def get_account_id(description: str) -> str:
    """Helper to detect account ID from description keywords."""
    desc_lower = description.lower()
    for keyword, acc_id in ACCOUNTS_MAP.items():
        if keyword.lower() in desc_lower:
            return acc_id
    return DEFAULT_ACCOUNT_ID



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
    if not result:
        # Level 2
        result = get_category_fuzzy(description)
    
    if not result:
        # Level 3
        result = get_category_gemini(description)

    # Add account detection
    result["budgetbakers_account_id"] = get_account_id(description)
    
    return result
