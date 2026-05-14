from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from database import get_db_connection
from parser import parse_transactions
from categorizer import determine_category
from audio_processor import transcribe_audio

app = FastAPI(title="Expense Processing API")

class TextProcessRequest(BaseModel):
    text: str

def process_and_store_transactions(text: str) -> dict:
    parsed_items = parse_transactions(text)
    if not parsed_items:
        raise HTTPException(status_code=400, detail="Could not parse any transactions from the provided text.")
        
    results = []
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for item in parsed_items:
        desc = item["description"]
        amount = item["amount"]
        
        category = determine_category(desc)
        
        # Store in staging
        cursor.execute(
            """
            INSERT INTO transactions_staging (amount, description, category)
            VALUES (?, ?, ?)
            """,
            (amount, desc, category)
        )
        
        results.append({
            "amount": amount,
            "description": desc,
            "category": category
        })
        
    conn.commit()
    conn.close()
    
    return {"message": "Transactions processed successfully", "transactions": results}

@app.post("/process-text")
async def process_text(request: TextProcessRequest):
    return process_and_store_transactions(request.text)

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    # Simple check for audio mime types
    if not file.content_type.startswith("audio/") and not file.content_type.startswith("application/ogg") and not file.filename.endswith(('.ogg', '.mp3', '.wav', '.m4a')):
        raise HTTPException(status_code=400, detail="File uploaded is not an audio file.")
        
    file_bytes = await file.read()
    
    try:
        transcription = transcribe_audio(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")
        
    if not transcription:
        raise HTTPException(status_code=400, detail="Audio transcribed to empty text.")
        
    response = process_and_store_transactions(transcription)
    response["transcription"] = transcription
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
