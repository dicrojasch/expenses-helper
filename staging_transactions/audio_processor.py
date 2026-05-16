from faster_whisper import WhisperModel
import os
import tempfile
import re

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
        prompt = "25000 café en efectivo \
            15000 almuerzo con tarjeta de credito davivienda \
            5000 taxi con tarjeta de credito nu bank \
            12500 gasolina con nequi \
            20000 consulta medica con caja social diego \
            20000 consulta medica con caja social cate \
            20000 desayuno con tarjeta de credito cencosud"
        segments, info = whisper_model.transcribe(
            tmp_path,
            beam_size=5,
            language="es",
            condition_on_previous_text=False,
            initial_prompt=prompt,
        )

        text = " ".join([segment.text for segment in segments])
        text = text.lower().strip()
        text = re.sub(r"[^a-zñáéíóú0-9\s\-,]", "", text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"([a-zñáéíóú])\s+(?=\d)", r"\1, ", text)
        return text.strip()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
