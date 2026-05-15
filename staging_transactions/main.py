from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from staging_transactions.database import get_db_connection
from staging_transactions.parser import parse_transactions
from staging_transactions.categorizer import determine_category
from staging_transactions.audio_processor import transcribe_audio

from staging_transactions.budgetbakers_sync.upload_transactions import (
    upload_transaction,
)

app = FastAPI(title="Expense Processing API")

# Default BudgetBakers Configuration
# TODO: Move these to environment variables or a configuration file
BB_DEFAULT_ACCOUNT_ID = "55e461be-cf71-49a1-9b1c-2c436f3ba29c"
BB_DEFAULT_CURRENCY_ID = "0df2d8a0-f26b-46bb-8b14-986139a6cbd7"
BB_DEFAULT_CATEGORY_ID = "00b4a7be-01a9-44f5-ba87-4745411d819d"  # 'Others' or default


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
        category_data = determine_category(desc)
        results.append(
            {
                "amount": amount,
                "description": desc,
                "category": category_data["category"],
                "budgetbakers_category_id": category_data["budgetbakers_category_id"],
                "budgetbakers_account_id": category_data["budgetbakers_account_id"],
            }
        )

    # Now open connection just for the bulk insert
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for res in results:
            cursor.execute(
                """
                INSERT INTO transactions_staging (amount, description, category, budgetbakers_category_id, budgetbakers_account_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    res["amount"],
                    res["description"],
                    res["category"],
                    res["budgetbakers_category_id"],
                    res["budgetbakers_account_id"],
                ),
            )
        conn.commit()
    finally:
        conn.close()

    # Additionally upload to BudgetBakers
    upload_results = []
    for res in results:
        try:
            bb_payload = {
                "accountId": res["budgetbakers_account_id"],
                "categoryId": res["budgetbakers_category_id"],
                "amount": res["amount"],
                "currencyId": BB_DEFAULT_CURRENCY_ID,
                # TODO: Change this when we have a better way to get the payee    "payee": "user input"
                "note": f"{res['description']}\nAuto-categorized as: {res['category']}",
            }
            success = upload_transaction(bb_payload)
            upload_results.append(
                {"description": res["description"], "success": bool(success)}
            )
        except Exception as e:
            print(f"Failed to upload transaction to BudgetBakers: {e}")
            upload_results.append(
                {"description": res["description"], "success": False, "error": str(e)}
            )

    return {
        "message": "Transactions processed and uploaded successfully",
        "transactions": results,
        "budgetbakers_sync": upload_results,
    }


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
