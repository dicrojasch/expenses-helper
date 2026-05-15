from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from staging_transactions.database import get_db_connection
from staging_transactions.parser import parse_transactions
from staging_transactions.categorizer import determine_category
from staging_transactions.audio_processor import transcribe_audio

app = FastAPI(title="Expense Processing API")


class TextProcessRequest(BaseModel):
    body: str


def process_and_store_transactions(text: str) -> dict:
    parsed_items = parse_transactions(text)
    if not parsed_items:
        raise HTTPException(
            status_code=400,
            detail="Could not parse any transactions from the provided text.",
        )

    # Level 3 categorization (Gemini) might open its own DB connection to cache results.
    # To avoid 'database is locked', we categorize everything FIRST before 
    # opening our own writing connection.
    results = []
    for item in parsed_items:
        desc = item["description"]
        amount = item["amount"]
        category = determine_category(desc)
        results.append({
            "amount": amount,
            "description": desc,
            "category": category
        })

    # Now open connection just for the bulk insert
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for res in results:
            cursor.execute(
                """
                INSERT INTO transactions_staging (amount, description, category)
                VALUES (?, ?, ?)
                """,
                (res["amount"], res["description"], res["category"]),
            )
        conn.commit()
    finally:
        conn.close()

    return {"message": "Transactions processed successfully", "transactions": results}


@app.post("/process-text")
async def process_text(request: TextProcessRequest):
    print("Processing text...")
    return process_and_store_transactions(request.body)


@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    # Simple check for audio mime types
    if (
        not file.content_type.startswith("audio/")
        and not file.content_type.startswith("application/ogg")
        and not file.filename.endswith((".ogg", ".mp3", ".wav", ".m4a"))
    ):
        raise HTTPException(
            status_code=400, detail="File uploaded is not an audio file."
        )

    file_bytes = await file.read()

    try:
        transcription = transcribe_audio(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error transcribing audio: {str(e)}"
        )

    if not transcription:
        raise HTTPException(status_code=400, detail="Audio transcribed to empty text.")

    response = process_and_store_transactions(transcription)
    response["transcription"] = transcription
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("staging_transactions.main:app", host="0.0.0.0", port=8000, reload=True)
