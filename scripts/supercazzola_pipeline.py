#!/usr/bin/env python3
"""
supercazzola_pipeline.py
========================
Pipeline unificata per l'Indice Supercazzola.

Flusso:
  1. Scarica testi freschi dai feed RSS di ogni partito
  2. Se il feed non è disponibile, usa i testi di fallback
  3. Passa i testi a Gemini per la valutazione della "fuffa"
  4. Salva il risultato in public/data/supercazzola_data.json

Uso:
    python3 scripts/supercazzola_pipeline.py

Dipendenze (requirements.txt):
    feedparser requests google-generativeai python-dotenv
"""

import os
import json
import re
import datetime
from pathlib import Path

try:
    import feedparser
    import requests
    import google.generativeai as genai
    from dotenv import load_dotenv
except ImportError as e:
    raise SystemExit(f"Dipendenza mancante: {e}. Esegui: pip install -r scripts/requirements.txt")

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise SystemExit(
        "ERRORE: GEMINI_API_KEY non impostata.\n"
        "Imposta il secret nel repository GitHub oppure crea scripts/.env"
    )

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Tempo massimo per ogni richiesta HTTP (secondi)
FETCH_TIMEOUT = 10
# Numero massimo di articoli per feed
MAX_ARTICLES = 15

# ---------------------------------------------------------------------------
# Partiti e feed RSS
# ---------------------------------------------------------------------------
PARTIES = [
    {
        "id": "FdI",
        "name": "Fratelli d'Italia",
        "color": "#0D47A1",
        "feeds": ["https://www.fratelli-italia.it/feed/"],
        "fallback": [
            "Il Governo sta lavorando con concretezza e determinazione per attuare il cronoprogramma previsto dalla legge di bilancio, valorizzando le risorse del PNRR in sinergia con gli enti locali.",
            "Dobbiamo fare sistema per affrontare la grande sfida della transizione digitale ed ecologica, portando a terra i risultati attesi dalla cabina di regia nazionale.",
            "Valorizzazione del made in Italy come driver fondamentale per la resilienza del sistema produttivo italiano in un contesto di benchmark europeo.",
        ],
    },
    {
        "id": "PD",
        "name": "Partito Democratico",
        "color": "#E53935",
        "feeds": ["https://www.partitodemocratico.it/feed/"],
        "fallback": [
            "La transizione ecologica deve essere inclusiva e sostenibile: questo è il nostro progetto paese per le prossime legislature.",
            "Serve un grande patto sociale per fare rete tra cittadini, istituzioni e imprese, con una governance chiara e condivisa dal territorio.",
            "L'implementazione del framework europeo richiede coesione e una visione strategica di lungo periodo, non slogan populisti.",
        ],
    },
    {
        "id": "M5S",
        "name": "MoVimento 5 Stelle",
        "color": "#F9A825",
        "feeds": ["https://www.movimento5stelle.eu/feed/"],
        "fallback": [
            "La gente non ne può più di questa politica! Dobbiamo fare sistema contro i privilegi e portare a terra le risorse del superbonus.",
            "Dopo un lavoro di ascolto diffuso su tutto il territorio nazionale, articolato in oltre 100 spazi di confronto e partecipazione, il percorso entra nella fase più avanzata e strategica.",
            "Efficientamento della pubblica amministrazione: non parole ma fatti. Un cambio di passo reale per i cittadini che meritano risposte concrete.",
        ],
    },
    {
        "id": "Lega",
        "name": "Lega",
        "color": "#1B5E20",
        "feeds": ["https://www.leganord.org/feed/", "https://lega-online.it/feed/"],
        "fallback": [
            "La sicurezza è il primo driver del benessere sociale: servono risorse concrete e un cronoprogramma chiaro per le forze dell'ordine.",
            "Il green deal europeo è un framework ideologico che penalizza le imprese italiane: serve discontinuità e concretezza.",
            "Valorizzazione dell'autonomia regionale come benchmark di efficienza: ogni territorio sa meglio di Roma di cosa ha bisogno.",
        ],
    },
    {
        "id": "FI",
        "name": "Forza Italia",
        "color": "#1565C0",
        "feeds": ["https://www.forza-italia.it/feed"],
        "fallback": [
            "La resilienza del sistema economico italiano dipende dalla capacità di fare rete tra pubblica amministrazione e settore privato.",
            "Serve una cabina di regia efficace per l'implementazione del PNRR, con governance chiara e stakeholder coinvolti.",
            "La sfida della digitalizzazione richiede un cambio di passo: portare a terra l'innovazione tecnologica con concretezza.",
        ],
    },
    {
        "id": "AVS",
        "name": "Alleanza Verdi Sinistra",
        "color": "#2E7D32",
        "feeds": ["https://europa-verde.it/feed/"],
        "fallback": [
            "La transizione ecologica deve essere giusta e inclusiva: nessuno deve essere lasciato indietro nel percorso verso la sostenibilità.",
            "L'implementazione della transizione energetica richiede governance multilivello e ascolto del territorio, non solo benchmark europei.",
            "Efficientamento energetico e valorizzazione dei beni comuni: questo è il nostro progetto paese per le prossime generazioni.",
        ],
    },
    {
        "id": "Azione",
        "name": "Azione",
        "color": "#0288D1",
        "feeds": ["https://www.azione.it/feed/"],
        "fallback": [
            "Serve un framework di riforma strutturale per riportare l'Italia ai livelli di competitività internazionale attraverso un cambio di passo nelle politiche industriali ed educative.",
            "La governance pubblica deve essere efficiente e trasparente: basta con le cabine di regia che producono solo documenti e non portano a terra i risultati.",
        ],
    },
    {
        "id": "IV",
        "name": "Italia Viva",
        "color": "#EF6C00",
        "feeds": ["https://www.italiaviva.it/feed/"],
        "fallback": [
            "Il cronoprogramma del governo non è credibile: mettere a terra le riforme richiede concretezza esecutiva, non cabine di regia vuote create solo per accontentare le correnti.",
            "Serve discontinuità rispetto al passato: un'agenda riformista chiara che non si perda in slogan ma porti risultati misurabili per i cittadini.",
        ],
    },
]

# ---------------------------------------------------------------------------
# Prompt Gemini
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """\
Sei un analista linguistico esperto di comunicazione politica italiana.
Analizza i seguenti testi tratti da comunicati di un partito politico e misura il livello di "Supercazzola":
l'uso di linguaggio inutilmente complesso, vuoto o eccessivamente astratto.

Testi:
{texts}

Restituisci SOLO JSON valido, senza markdown, senza blocchi ```json```.

Formato:
{{
  "metrics": {{
    "complessita_periodi": <float 0-100>,
    "vuoto_semantico": <float 0-100, alto se si usano parole grosse per dire nulla>,
    "fuffa_index": <float 0-100, punteggio aggregato>,
    "astrazione_concettuale": <float 0-100, quanto si vola alto invece di essere concreti>
  }},
  "top_samples": [
    {{
      "text": "<testo originale intero più rappresentativo, max 400 caratteri>",
      "score": <float 0-100>,
      "convoluted_phrases": [
        "<sotto-stringa esatta del testo che rappresenta fuffa o giro di parole>",
        "<seconda sotto-stringa (se presente)>"
      ]
    }}
  ]
}}
"""

# ---------------------------------------------------------------------------
# Funzioni
# ---------------------------------------------------------------------------

def clean_html(text: str) -> str:
    """Rimuove tag HTML e normalizza spazi."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_texts(feeds: list[str]) -> list[str]:
    """Tenta di scaricare testi dai feed RSS. Ritorna lista di stringhe pulite."""
    texts = []
    for url in feeds:
        try:
            d = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in d.entries[:MAX_ARTICLES]:
                content = ""
                if hasattr(entry, "summary"):
                    content += entry.summary + " "
                if hasattr(entry, "content"):
                    for c in entry.content:
                        content += c.value + " "
                cleaned = clean_html(content)
                if len(cleaned) > 80:
                    texts.append(cleaned)
        except Exception as e:
            print(f"    RSS {url} non disponibile: {e}")
    return texts


def evaluate_with_gemini(party_id: str, texts: list[str]) -> dict | None:
    """Chiama Gemini con i testi del partito e ritorna le metriche."""
    sample_texts = texts[:10]  # max 10 testi per contenere i token
    texts_str = "\n".join(f"- {t[:500]}" for t in sample_texts)
    prompt = PROMPT_TEMPLATE.format(texts=texts_str)

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Pulizia robusta: rimuove blocchi markdown se il modello li inserisce
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw.strip())
    except Exception as e:
        print(f"    Gemini error ({party_id}): {e}")
        return None


def process_party(party: dict) -> dict | None:
    """Scarica testi, valuta con Gemini e costruisce il record del partito."""
    print(f"  ▸ {party['name']}")

    # 1. Tenta fetch RSS
    texts = fetch_texts(party["feeds"])

    # 2. Fallback se feed offline
    if not texts:
        print(f"    → Feed non disponibili, uso testi di fallback")
        texts = party["fallback"]

    print(f"    → {len(texts)} testi acquisiti")

    # 3. Valutazione Gemini
    gemini_result = evaluate_with_gemini(party["id"], texts)

    if gemini_result is None:
        # Fallback numerico neutro se Gemini fallisce
        print(f"    → Gemini fallito, uso valori neutri")
        gemini_result = {
            "metrics": {
                "complessita_periodi": 50,
                "vuoto_semantico": 50,
                "fuffa_index": 50,
                "astrazione_concettuale": 50,
            },
            "top_samples": [
                {
                    "text": texts[0][:400] if texts else "",
                    "score": 50,
                    "convoluted_phrases": [],
                }
            ],
        }

    m = gemini_result["metrics"]
    return {
        "id": party["id"],
        "name": party["name"],
        "color": party["color"],
        "n_testi": len(texts),
        "used_fallback": len(fetch_texts(party["feeds"])) == 0,
        "radar": {
            "Complessità Periodi": float(m.get("complessita_periodi", 50)),
            "Vuoto Semantico": float(m.get("vuoto_semantico", 50)),
            "Indice di Fuffa": float(m.get("fuffa_index", 50)),
            "Astrazione Concettuale": float(m.get("astrazione_concettuale", 50)),
        },
        "top_samples": gemini_result.get("top_samples", []),
    }


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_path = project_root / "public" / "data" / "supercazzola_data.json"

    print("=== Supercazzola Pipeline ===")
    print(f"Avvio: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    parties_output = []
    for party in PARTIES:
        result = process_party(party)
        if result:
            parties_output.append(result)
        print()

    output = {
        "generated_at": datetime.datetime.now().isoformat(),
        "parties": parties_output,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Salvato: {output_path}")
    print(f"   Partiti: {len(parties_output)}")


if __name__ == "__main__":
    main()
