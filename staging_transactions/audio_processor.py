from faster_whisper import WhisperModel
import os
import tempfile

# Initialize model once (globally) to save load time. 
# Using "base" for lightweight local processing.
MODEL_SIZE = "base"
model = None

def get_model():
    global model
    if model is None:
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return model

def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    _, ext = os.path.splitext(filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
        
    try:
        whisper_model = get_model()
        segments, info = whisper_model.transcribe(tmp_path, beam_size=5)
        
        text = " ".join([segment.text for segment in segments])
        return text.strip()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
