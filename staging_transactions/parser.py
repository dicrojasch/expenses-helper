import re

def parse_transactions(text: str) -> list[dict]:
    """
    Parses a string containing transactions in the format:
    Price1 - Description1, Price2 - Description2...
    """
    # Regex to capture amount and description
    # Matches a number (with dots/commas) followed by '-' and then captures everything 
    # until it finds a comma followed by another number and '-' or end of string.
    pattern = r"([\d.,]+)\s*-\s*(.*?)(?=\s*,\s*[\d.,]+\s*-|$)"
    
    matches = re.findall(pattern, text)
    
    transactions = []
    for amount_str, description in matches:
        description = description.strip()
        
        # Normalize amount
        # Remove dots (thousands separator in Colombia)
        normalized_amount_str = amount_str.replace('.', '')
        # Replace comma (decimal separator) with dot
        normalized_amount_str = normalized_amount_str.replace(',', '.')
        
        try:
            amount = float(normalized_amount_str)
            transactions.append({
                "amount": amount,
                "description": description
            })
        except ValueError:
            # Skip if conversion fails
            continue
            
    return transactions
