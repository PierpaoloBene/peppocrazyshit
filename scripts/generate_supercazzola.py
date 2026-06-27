import os
import json
import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Carica variabili d'ambiente (es. GEMINI_API_KEY)
load_dotenv()

# Configura l'API di Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERRORE: La variabile d'ambiente GEMINI_API_KEY non è impostata.")
    print("Crea un file .env nella cartella scripts con: GEMINI_API_KEY=la_tua_chiave")
    exit(1)

genai.configure(api_key=API_KEY)

# Usa il modello Flash per essere veloci ed efficienti nei costi
model = genai.GenerativeModel('gemini-1.5-flash')

# Definiamo i partiti con alcuni testi di esempio (in un'app reale questi verrebbero presi da feed RSS o scraper)
PARTIES = [
    {
        "id": "FdI",
        "name": "Fratelli d'Italia",
        "color": "#0D47A1",
        "texts": [
            "I dati preliminari Istat raccontano una realtà che per troppo tempo in molti hanno considerato impossibile: il Mezzogiorno registra una crescita del Pil dello 0,6% e guida il Paese anche sul fronte occupazionale.",
            "Il nuovo piano Transizione 5.0 è un successo. La dimostrazione che il governo raccoglie preziosi risultati con una misura organica da qua al futuro."
        ]
    },
    {
        "id": "PD",
        "name": "Partito Democratico",
        "color": "#E53935",
        "texts": [
            "L'implementazione del framework europeo richiede coesione e una visione strategica di lungo periodo, non slogan populisti.",
            "Serve un grande patto sociale per fare rete tra cittadini, istituzioni e imprese, con una governance chiara e condivisa dal territorio."
        ]
    },
    {
        "id": "M5S",
        "name": "MoVimento 5 Stelle",
        "color": "#F9A825",
        "texts": [
            "Dopo un lavoro di ascolto diffuso su tutto il territorio nazionale, articolato in oltre 100 spazi di confronto e partecipazione, il percorso di Nova entra nella fase più avanzata e strategica.",
            "Costruiamo un sistema più chiaro e coerente attraverso tre strumenti: l’aggiornamento del Piano Paesaggistico Regionale, la nostra legge regionale sulle aree idonee e il coinvolgimento dal basso."
        ]
    },
    {
        "id": "Lega",
        "name": "Lega",
        "color": "#1B5E20",
        "texts": [
            "Il green deal europeo è un framework ideologico che penalizza le imprese italiane: serve discontinuità e concretezza.",
            "La transizione ecologica non può essere imposta dall'alto: serve un tavolo di confronto che ascolti la gente e le imprese del nostro territorio produttivo."
        ]
    },
    {
        "id": "FI",
        "name": "Forza Italia",
        "color": "#1565C0",
        "texts": [
            "La sfida della digitalizzazione richiede un cambio di passo: portare a terra l'innovazione tecnologica con concretezza e pragmatismo.",
            "Serve una cabina di regia efficace per l'implementazione del PNRR, con governance chiara e stakeholder coinvolti fin dalle prime fasi decisionali."
        ]
    },
    {
        "id": "AVS",
        "name": "Alleanza Verdi Sinistra",
        "color": "#2E7D32",
        "texts": [
            "L'implementazione della transizione energetica richiede governance multilivello e ascolto del territorio, non solo sterili benchmark europei dettati dalla tecnocrazia.",
            "Serve un grande patto sociale per fare sistema contro il cambiamento climatico, valorizzando le energie rinnovabili come driver primario di crescita."
        ]
    },
    {
        "id": "Azione",
        "name": "Azione",
        "color": "#0288D1",
        "texts": [
            "Serve un framework di riforma strutturale per riportare l'Italia ai livelli di competitività internazionale attraverso un cambio di passo nelle politiche industriali ed educative."
        ]
    },
    {
        "id": "IV",
        "name": "Italia Viva",
        "color": "#EF6C00",
        "texts": [
            "Il cronoprogramma del governo non è credibile: mettere a terra le riforme richiede concretezza esecutiva, non cabine di regia vuote create solo per accontentare le correnti."
        ]
    },
    {
        "id": "SI",
        "name": "Sinistra Italiana",
        "color": "#B71C1C",
        "texts": [
            "La transizione ecologica deve valorizzare il lavoro e la coesione sociale: non è accettabile una governance che non ascolti i lavoratori e le comunità territoriali marginalizzate."
        ]
    },
    {
        "id": "PiuEu",
        "name": "Più Europa",
        "color": "#512DA8",
        "texts": [
            "Solo attraverso un'integrazione europea più profonda possiamo affrontare le sfide globali: serve resilienza istituzionale e coesione strutturale tra tutti gli stakeholder europei."
        ]
    }
]

PROMPT_TEMPLATE = """
Sei un analista linguistico ed esperto di comunicazione politica italiana.
Devi analizzare i seguenti estratti di comunicati politici per misurare il livello di "Supercazzola" (ovvero l'uso di linguaggio inutilmente complesso, vuoto o eccessivamente astratto).

Testi forniti:
{texts}

Per favore, restituisci l'output ESATTAMENTE nel seguente formato JSON puro, senza markdown, senza blocchi di codice ```json, senza commenti. Solo il JSON validabile.

Formato richiesto:
{{
  "metrics": {{
    "complessita_periodi": <float da 0 a 100>,
    "vuoto_semantico": <float da 0 a 100, alto se si usano parole grosse per dire nulla>,
    "fuffa_index": <float da 0 a 100, punteggio aggregato>,
    "astrazione_concettuale": <float da 0 a 100, quanto si vola alto invece di essere concreti>
  }},
  "top_samples": [
    {{
      "text": "<Il testo originale intero (scegli il più rappresentativo)>",
      "score": <float da 0 a 100 del singolo testo>,
      "convoluted_phrases": [
        "<sotto-stringa esatta dal testo 1 che rappresenta un giro di parole o fuffa>",
        "<sotto-stringa esatta dal testo 2 (se presente)>"
      ]
    }}
  ]
}}
"""

def evaluate_party(party):
    print(f"Valutando: {party['name']}...")
    texts_str = "\n".join([f"- {t}" for t in party['texts']])
    prompt = PROMPT_TEMPLATE.format(texts=texts_str)
    
    try:
        response = model.generate_content(prompt)
        # Pulisci eventuale formattazione markdown in caso il modello la inserisca nonostante le istruzioni
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        data = json.loads(raw_text.strip())
        
        return {
            "id": party["id"],
            "name": party["name"],
            "color": party["color"],
            "n_testi": len(party["texts"]),
            "radar": {
                "Complessità Periodi": data["metrics"]["complessita_periodi"],
                "Vuoto Semantico": data["metrics"]["vuoto_semantico"],
                "Indice di Fuffa": data["metrics"]["fuffa_index"],
                "Astrazione Concettuale": data["metrics"]["astrazione_concettuale"]
            },
            "top_samples": data["top_samples"]
        }
    except Exception as e:
        print(f"Errore nella valutazione di {party['name']}: {e}")
        # Ritorna fallback
        return {
            "id": party["id"],
            "name": party["name"],
            "color": party["color"],
            "n_testi": len(party["texts"]),
            "radar": {
                "Complessità Periodi": 50,
                "Vuoto Semantico": 50,
                "Indice di Fuffa": 50,
                "Astrazione Concettuale": 50
            },
            "top_samples": [
                {
                    "text": party['texts'][0],
                    "score": 50,
                    "convoluted_phrases": []
                }
            ]
        }

def main():
    final_data = {
        "generated_at": datetime.datetime.now().isoformat(),
        "parties": []
    }
    
    for party in PARTIES:
        evaluated = evaluate_party(party)
        final_data["parties"].append(evaluated)
        
    # Salva il file
    output_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'supercazzola_data.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Dati generati con successo in {output_path}")

if __name__ == "__main__":
    main()
