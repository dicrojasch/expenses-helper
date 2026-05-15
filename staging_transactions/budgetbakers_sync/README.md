# BudgetBakers Sync - Setup & Usage

This module automates transaction uploads to BudgetBakers (Wallet) by reverse-engineering their internal API.

## 1. Installation

To use this module, run:

```bash
pip install playwright && playwright install chromium
```

## 2. Workflow

### Step 1: Set Authentication Cookies
Since you are managing cookies manually:
1. Open `staging_transactions/budgetbakers_sync/cookies.json`.
2. Update the `"cookie_header"` field with your raw cookie string (e.g., `name=value; name2=value2`).
3. You can get this string from your browser's Developer Tools (F12 > Network > Headers > Cookie).

### Step 2: Upload Transactions
Use the uploader script in your pipeline:
```bash
python staging_transactions/budgetbakers_sync/upload_transactions.py
```

## 3. Configuration
Ensure you have updated the `accountId` and `categoryId` in `upload_transactions.py` with your personal internal IDs from BudgetBakers.
