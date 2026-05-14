import os
import google.generativeai as genai
from rapidfuzz import process, fuzz
from database import get_db_connection

# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

def get_category_from_db(description: str) -> str | None:
    """Level 1: Exact match in SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category FROM category_mapping WHERE description = ?", (description,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result["category"]
    return None

def get_category_fuzzy(description: str) -> str | None:
    """Level 2: Fuzzy Matching (>90% confidence)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT description, category FROM category_mapping")
    mappings = cursor.fetchall()
    conn.close()
    
    if not mappings:
        return None
        
    choices = {row["description"]: row["category"] for row in mappings}
    
    match = process.extractOne(description, choices.keys(), scorer=fuzz.WRatio)
    
    if match:
        matched_str, score, _ = match
        if score > 90:
            return choices[matched_str]
            
    return None

def get_category_gemini(description: str) -> str:
    """Level 3: Gemini Fallback."""
    if not GENAI_API_KEY:
        return "Uncategorized"
        
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        You are a financial categorizer. Classify the following expense description into a single short category.
        Return ONLY the category name. Keep it brief (1-3 words).
        Example categories: Food, Transport, Utilities, Entertainment, Health, Shopping.
        
        Description: "{description}"
        Category:
        """
        response = model.generate_content(prompt)
        category = response.text.strip()
        
        # Save to DB for future caching
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO category_mapping (description, category) VALUES (?, ?)", 
            (description, category)
        )
        conn.commit()
        conn.close()
        
        return category
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "Uncategorized"

def determine_category(description: str) -> str:
    """Main categorizer function implementing the 3 priority levels."""
    # Level 1
    category = get_category_from_db(description)
    if category:
        return category
        
    # Level 2
    category = get_category_fuzzy(description)
    if category:
        return category
        
    # Level 3
    return get_category_gemini(description)
