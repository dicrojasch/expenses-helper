# Expenses Helper API

A Python-based API designed to process expense transactions sent via text or audio (WhatsApp). It features local audio transcription, smart parsing, and a 3-level categorization engine to minimize external API costs.

## 🚀 Features

- **Local Transcription**: Uses `faster-whisper` to transcribe audio locally without external costs.
- **Smart Parsing**: RegEx-based extraction of amounts and descriptions with support for regional number formats (Colombia).
- **3-Level Categorization Engine**:
    1.  **Cache (SQLite)**: Immediate lookup for known descriptions.
    2.  **Fuzzy Matching**: Uses `rapidfuzz` (>90% confidence) to match similar descriptions.
    3.  **Gemini Fallback**: Uses Gemini 2.0 Flash for Spanish classification, automatically mapping to BudgetBakers UUIDs.
- **BudgetBakers Sync**: Real-time synchronization with Wallet (BudgetBakers) using their CouchDB bulk-update internal API.
- **Persistence**: SQLite database with support for transaction staging and category-to-UUID mappings.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd expenses-helper
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install playwright && playwright install chromium
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```

## 🔐 Authentication (BudgetBakers)

To enable synchronization, you must manually provide session headers in `config/cookies.json`:

1.  Open `config/cookies.json` (created automatically on first run if missing).
```json
{
    "cookie_header": "your_full_cookie_string",
    "auth_header": "Basic OGVlZjJm..."
}
```
*Note: You can extract these from your browser's Developer Tools (F12) by inspecting requests to `web.budgetbakers.com`.*

## 🏃 Running the Application

Start the FastAPI server:
```bash
uvicorn staging_transactions.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 API Endpoints

### `POST /process-text`
Receives a JSON with the message text.
- **Payload**: `{"body": "15000 - Almuerzo, 5000 - Café"}`

### `POST /process-audio`
Receives an audio file (form-data).
- **Format**: `.ogg`, `.mp3`, `.wav`, `.m4a`

## 🗄️ Database Structure

- `category_mapping`: Stores `description` -> `category` and `budgetbakers_category_id`.
- `transactions_staging`: Stores processed transactions including the UUID for sync.

## 📝 License

MIT
