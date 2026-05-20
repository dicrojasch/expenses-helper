from faster_whisper import WhisperModel
import os
import tempfile
import re
import json

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
        # Load accounts from configuration file to parameterize prompt
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        accounts_path = os.path.join(root_dir, "config", "accounts_map.json")
        accounts = []
        if os.path.exists(accounts_path):
            try:
                with open(accounts_path, "r", encoding="utf-8") as f:
                    accounts_map = json.load(f)
                    accounts = list(accounts_map.keys())
            except Exception as e:
                print(f"Error loading accounts_map.json: {e}")
        else:
            accounts = [
                "tarjeta de crédito davivienda",
                "nequi cate",
                "efectivo",
                "caja social cate",
                "caja social diego",
                "daviplata",
                "tarjeta credito nu",
                "tarjeta credito cencosud"
            ]
        prompt_lines = [
            "25000 café",
            "15000 almuerzo",
            "5000 taxi",
            "12500 gasolina",
            "13500 consulta medica",
            "200000 mercado d1",
            "55820 mercado olimpica",
            "34000 mercado jumbo",
            "539000 cosas bebe",
            "855800 recarga tu llave"
        ]

        final_lines = []
        n_prompts = len(prompt_lines)
        n_accounts = len(accounts)
        limit = max(n_prompts, n_accounts)
        for i in range(limit):
            p = prompt_lines[i % n_prompts]
            a = accounts[i % n_accounts]
            final_lines.append(f"{p} con {a}")
        final_lines.append("12500 onces panaderia en efectivo")
        prompt = " ".join(final_lines)
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
