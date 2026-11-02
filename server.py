"""Fake News Checker — server Flask + OpenAI API.

Avvio:  python server.py   (richiede OPENAI_API_KEY nel file .env o nell'ambiente)
"""

import json
import os

import openai
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from openai import OpenAI

load_dotenv()

app = Flask(__name__, static_folder="static")

# Modello OpenAI: cambialo nel file .env con OPENAI_MODEL se vuoi (es. gpt-5-mini)
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

SYSTEM_PROMPT = """Sei un fact-checker rigoroso. Ricevi una frase pronunciata a voce \
(trascritta automaticamente, quindi tollera piccoli errori di trascrizione) e devi \
valutarne la correttezza fattuale con un voto da 1 a 10.

Criteri di valutazione:
- 9-10: affermazione vera e verificabile, senza distorsioni.
- 7-8: sostanzialmente vera, con imprecisioni minori o semplificazioni.
- 5-6: parzialmente vera, fuorviante, o mescola fatti veri con conclusioni discutibili.
- 3-4: in gran parte scorretta o priva di fondamento.
- 1-2: falsa. Le affermazioni FALSE vanno penalizzate moltissimo: se il nucleo della \
frase è falso, il voto deve essere 1 o 2, anche se contiene dettagli veri.

Regole:
- Se la frase è un'opinione, una domanda o non contiene affermazioni fattuali \
verificabili, usa "verificabile": false e assegna voto 5 con spiegazione.
- Se il voto è basso (sotto 7), elenca in "motivi" le ragioni specifiche, indicando \
quali parti sono false o fuorvianti e qual è invece la realtà dei fatti.
- Se il voto è alto, "motivi" può essere una lista vuota o contenere brevi conferme.
- Rispondi sempre in italiano.
- Rispondi SOLO con il JSON richiesto, senza testo aggiuntivo."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "voto": {
            "type": "integer",
            "enum": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "description": "Voto di correttezza fattuale da 1 a 10",
        },
        "verificabile": {
            "type": "boolean",
            "description": "False se la frase è un'opinione o non contiene fatti verificabili",
        },
        "giudizio": {
            "type": "string",
            "description": "Sintesi del giudizio in una frase",
        },
        "motivi": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Motivi specifici del voto, obbligatori se il voto è basso",
        },
    },
    "required": ["voto", "verificabile", "giudizio", "motivi"],
    "additionalProperties": False,
}

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


def _chiedi_valutazione(frase: str, use_web: bool) -> str:
    """Chiama l'API OpenAI e restituisce il testo JSON della valutazione."""
    client = get_client()
    if use_web:
        # La ricerca web è disponibile tramite la Responses API
        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM_PROMPT,
            input=f'Valuta la correttezza di questa frase: "{frase}"',
            tools=[{"type": "web_search"}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "valutazione",
                    "schema": OUTPUT_SCHEMA,
                    "strict": True,
                }
            },
        )
        return response.output_text

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f'Valuta la correttezza di questa frase: "{frase}"',
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "valutazione",
                "schema": OUTPUT_SCHEMA,
                "strict": True,
            },
        },
    )
    return response.choices[0].message.content


@app.post("/api/check")
def check():
    data = request.get_json(silent=True) or {}
    frase = (data.get("text") or "").strip()
    if not frase:
        return jsonify({"error": "Nessuna frase da analizzare."}), 400

    use_web = bool(data.get("web_search"))

    if not os.environ.get("OPENAI_API_KEY"):
        return (
            jsonify(
                {
                    "error": "Chiave API mancante: crea un file .env con "
                    "OPENAI_API_KEY=... e riavvia il server."
                }
            ),
            401,
        )

    try:
        text = _chiedi_valutazione(frase, use_web)
    except openai.AuthenticationError:
        return (
            jsonify(
                {
                    "error": "Chiave API non valida o mancante. Imposta "
                    "OPENAI_API_KEY nel file .env."
                }
            ),
            401,
        )
    except openai.RateLimitError:
        return (
            jsonify({"error": "Limite di richieste (o credito esaurito), riprova tra poco."}),
            429,
        )
    except openai.APIStatusError as e:
        return jsonify({"error": f"Errore API ({e.status_code}): {e.message}"}), 502
    except openai.APIConnectionError:
        return jsonify({"error": "Impossibile raggiungere l'API di OpenAI."}), 502

    if not text:
        return jsonify({"error": "Risposta del modello vuota."}), 502

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return jsonify({"error": "Risposta del modello non interpretabile."}), 502

    result["frase"] = frase
    return jsonify(result)


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("ATTENZIONE: OPENAI_API_KEY non trovata. Crea un file .env "
              "(vedi .env.example) prima di usare l'app.")
    app.run(host="127.0.0.1", port=5000, debug=False)
