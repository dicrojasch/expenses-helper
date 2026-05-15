import json
import os
import requests
import sys
import uuid
from datetime import datetime, timezone

# Configuration
# Note: The owner ID in the URL should match your reservedOwnerId
OWNER_ID = "8eef2fc9-8b90-4aa7-a4fb-cf2381b7a445"
API_URL = f"https://couch-prod-us-1.budgetbakers.com/bb-{OWNER_ID}/_bulk_docs"
# Use absolute path for the cookies file relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(SCRIPT_DIR, "cookies.json")


def load_credentials():
    """Loads the cached cookie and auth headers from cookies.json."""
    try:
        if not os.path.exists(COOKIES_FILE):
            print(f"Notice: {COOKIES_FILE} not found. Creating empty template...")
            with open(COOKIES_FILE, "w") as f:
                json.dump({"cookie_header": "", "auth_header": ""}, f, indent=4)
            return None, None
            
        with open(COOKIES_FILE, "r") as f:
            data = json.load(f)
            return data.get("cookie_header"), data.get("auth_header")
    except Exception as e:
        print(f"Error reading credentials: {e}")
        sys.exit(1)


def upload_transaction(payload):
    """
    Sends a POST request to the BudgetBakers CouchDB API to create a record.
    """
    cookie_header, auth_header = load_credentials()
    
    if not cookie_header or not auth_header:
        print("\n[ERROR] Missing authentication credentials.")
        print("Please manually update 'cookies.json' with 'cookie_header' and 'auth_header'.")
        return False

    headers = {
        "Authorization": auth_header,
        "Cookie": cookie_header,
        "Content-Type": "application/json",
        "accept": "application/json",
        "accept-language": "es-US,es;q=0.9,en;q=0.8,es-419;q=0.7,gl;q=0.6",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Origin": "https://web.budgetbakers.com",
        "Referer": "https://web.budgetbakers.com/",
        "Connection": "keep-alive"
    }

    # Construct the CouchDB bulk_docs payload
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3] + "Z"
    record_id = f"Record_{uuid.uuid4()}"
    
    # BudgetBakers amounts are stored as integers (e.g., 10.50 -> 1050)
    amount_subunit = int(float(payload.get('amount', 0)) * 100)

    couch_doc = {
        "reservedCreatedAt": now_iso,
        "reservedUpdatedAt": now_iso,
        "reservedSource": "web",
        "reservedModelType": "Record",
        "reservedOwnerId": OWNER_ID,
        "reservedAuthorId": OWNER_ID,
        "type": 1,
        "currencyId": f"-Currency_{payload.get('currencyId')}",
        "accountId": f"-Account_{payload.get('accountId')}",
        "categoryId": f"-Category_{payload.get('categoryId')}",
        "recordDate": payload.get('recordDate', now_iso),
        "paymentType": 0,
        "recordState": 1,
        "transfer": False,
        "payee": payload.get('payee', ""),
        "note": payload.get('note', ""),
        "contactId": None,
        "amount": amount_subunit,
        "categoryConfirmReason": 4,
        "refAmount": amount_subunit,
        "_id": record_id
    }

    bulk_payload = {
        "docs": [couch_doc],
        "new_edits": True # Set to True for new records without manual rev handling
    }

    print(f"Uploading transaction to CouchDB: {payload.get('payee')} - {payload.get('amount')}...")

    try:
        response = requests.post(API_URL, headers=headers, json=bulk_payload)
        
        if response.status_code in [401, 403]:
            print("\n[WARNING] Authentication expired or invalid.")
            print("Please update your 'auth_header' and 'cookie_header' in 'cookies.json'.")
            return False
            
        response.raise_for_status()
        print(f"Success! Record created with ID: {record_id}")
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        if response.text:
            print(f"Response body: {response.text}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    # Test payload (IDs without prefixes as the script adds them)
    test_payload = {
        "accountId": "55e461be-cf71-49a1-9b1c-2c436f3ba29c",
        "categoryId": "00b4a7be-01a9-44f5-ba87-4745411d819d",
        "amount": 1224.45,
        "currencyId": "0df2d8a0-f26b-46bb-8b14-986139a6cbd7",
        "payee": "CouchDB Test",
        "note": "Automated CouchDB upload",
        "recordDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3] + "Z"
    }
    
    upload_transaction(test_payload)
