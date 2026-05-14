# Expenses Helper API

A Python-based API designed to process expense transactions sent via text or audio (WhatsApp). It features local audio transcription, smart parsing, and a 3-level categorization engine to minimize external API costs.

## 🚀 Features

- **Local Transcription**: Uses `faster-whisper` to transcribe audio locally without external costs.
- **Smart Parsing**: RegEx-based extraction of amounts and descriptions with support for regional number formats (Colombia).
- **3-Level Categorization Engine**:
    1.  **Cache (SQLite)**: Immediate lookup for known descriptions.
    2.  **Fuzzy Matching**: Uses `rapidfuzz` (>90% confidence) to match similar descriptions.
    3.  **Gemini Fallback**: Uses Gemini 1.5 Flash for new descriptions, automatically caching the result.
- **Persistence**: SQLite database for caching and transaction staging.

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
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and add your API key:
   ```bash
   cp .env.example .env
   ```

## 🏃 Running the Application

Start the FastAPI server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 API Endpoints

### `POST /process-text`
Receives a JSON with the message text.
- **Payload**: `{"text": "15000 - Lunch, 20.50 - Coffee"}`

### `POST /process-audio`
Receives an audio file (form-data).
- **Format**: `.ogg`, `.mp3`, `.wav`, `.m4a`

## 🗄️ Database Structure

- `category_mapping`: Stores `description` -> `category` for caching.
- `transactions_staging`: Stores processed transactions for further sync with other systems.

## 📝 License

MIT
