import os
from google import genai
from rapidfuzz import process, fuzz
from staging_transactions.database import get_db_connection

# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = None
if GENAI_API_KEY:
    client = genai.Client(api_key=GENAI_API_KEY)


def get_category_from_db(description: str) -> str | None:
    """Level 1: Exact match in SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category FROM category_mapping WHERE description = ?", (description,)
    )
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
    if not client:
        return "Uncategorized"

    try:
        prompt = f"""
        You are a financial assistant specialized in expense classification. 
        Your task is to categorize the following description into EXACTLY ONE category from the allowed list below.

        ALLOWED CATEGORIES:
        'Food & Drinks', 'Bar, cafe', 'Restaurant, fast-food', 'Groceries', 'Shopping', 
        'Drug-store, chemist', 'Leisure time', 'Stationery, tools', 'Gifts, joy', 
        'Electronics, accessories', 'Pets, animals', 'Home, garden', 'Health and beauty', 
        'Clothes & Footwear', 'Housing', 'Maintenance, repairs', 'Services', 
        'Energy, utilities', 'Rent', 'Transportation', 'Taxi', 'Public transport', 
        'Vehicle', 'Leasing', 'Vehicle insurance', 'Rentals', 'Vehicle maintenance', 
        'Parking', 'Fuel', 'Life & Entertainment', 'Lottery, gambling', 'Alcohol, tobacco', 
        'Charity, gifts', 'Holiday, trips, hotels', 'TV, Streaming', 'Books, audio, subscriptions', 
        'Education, development', 'Hobbies', 'Culture, sport events', 'Active sport, fitness', 
        'Wellness, beauty', 'Health care, doctor', 'Communication, PC', 'Software, apps, games', 
        'Internet', 'Telephony, mobile phone', 'Financial expenses', 'Child Support', 
        'Charges, Fees', 'Advisory', 'Loans, interests', 'Insurances', 'Investments', 
        'Savings', 'Income', 'Gifts', 'Refunds (tax, purchase)', 'Lending, renting', 
        'Dues & grants', 'Rental income', 'Sale', 'Interests, dividends', 'Wage, invoices', 'Others'

        RULES:
        1. Return ONLY the category name. 
        2. Do not include periods, explanations, or extra text.
        3. If the description is ambiguous, choose 'Others'.

        Description: "{description}"
        Category:"""

        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        category = response.text.strip()

        # Save to DB for future caching
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO category_mapping (description, category) VALUES (?, ?)",
            (description, category),
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
