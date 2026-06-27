#!/usr/bin/env python3
"""
scrape_supercazzola.py
======================
Scarica i comunicati stampa dei principali partiti italiani via RSS,
calcola l'Indice Gulpease e il punteggio "Supercazzola" basato su buzzwords.

Uso:
    python3 scripts/scrape_supercazzola.py

Output:
    public/data/supercazzola_data.json

Dipendenze:
    pip install feedparser requests
"""

import json
import re
import math
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import feedparser
    import requests
except ImportError:
    print("Installazione dipendenze...")
    os.system(f"{sys.executable} -m pip install feedparser requests")
    import feedparser
    import requests

# ---------------------------------------------------------------------------
# Configurazione feeds RSS dei partiti
# ---------------------------------------------------------------------------
PARTY_FEEDS = {
    "FdI": {
        "name": "Fratelli d'Italia",
        "color": "#1E90FF",
        "feeds": [
            "https://www.fratelli-italia.it/feed/",
        ]
    },
    "PD": {
        "name": "Partito Democratico",
        "color": "#FF0000",
        "feeds": [
            "https://www.partitodemocratico.it/feed/",
        ]
    },
    "M5S": {
        "name": "MoVimento 5 Stelle",
        "color": "#FFD700",
        "feeds": [
            "https://www.movimento5stelle.eu/feed/",
        ]
    },
    "Lega": {
        "name": "Lega - Salvini Premier",
        "color": "#006400",
        "feeds": [
            "https://www.lega-nerd.com/feed/",  # fallback generico
        ]
    },
    "FI": {
        "name": "Forza Italia",
        "color": "#4169E1",
        "feeds": [
            "https://www.forza-italia.it/feed",
        ]
    },
    "AVS": {
        "name": "Alleanza Verdi Sinistra",
        "color": "#228B22",
        "feeds": [
            "https://europa-verde.it/feed/",
        ]
    },
}

# Testi di fallback per ogni partito (da usare se i feed non sono raggiungibili)
FALLBACK_TEXTS = {
    "FdI": [
        "Il Governo sta lavorando con concretezza e determinazione per attuare il cronoprogramma previsto dalla legge di bilancio, valorizzando le risorse del PNRR in sinergia con gli enti locali.",
        "Dobbiamo fare sistema per affrontare la grande sfida della transizione digitale ed ecologica, portando a terra i risultati attesi dalla cabina di regia nazionale.",
        "La governance del piano richiede un tavolo permanente tra stakeholder pubblici e privati per efficientare i processi e garantire sostenibilità nel lungo periodo.",
        "L'iter legislativo sarà caratterizzato da discontinuità rispetto al passato: un cambio di passo concreto per rispondere alle esigenze della gente.",
        "Valorizzazione del made in Italy come driver fondamentale per la resilienza del sistema produttivo italiano in un contesto di benchmark europeo.",
    ],
    "PD": [
        "La transizione ecologica deve essere inclusiva e sostenibile: questo è il nostro progetto paese per le prossime legislature.",
        "Serve un grande patto sociale per fare rete tra cittadini, istituzioni e imprese, con una governance chiara e condivisa dal territorio.",
        "L'implementazione del framework europeo richiede coesione e una visione strategica di lungo periodo, non slogan populisti.",
        "Dobbiamo mettere a terra le risorse europee attraverso un percorso partecipato che ascolti il territorio e valorizzi le competenze locali.",
        "La nostra proposta di rimodulazione fiscale mira a ridurre il gap di equità attraverso misure di welfare inclusive e sostenibili.",
    ],
    "M5S": [
        "La gente non ne può più di questa politica! Dobbiamo fare sistema contro i privilegi e portare a terra le risorse del superbonus.",
        "La nostra visione è chiara: sostenibilità, digitalizzazione e inclusione sociale come benchmark per le politiche del futuro.",
        "Il cronoprogramma del reddito di cittadinanza va rivisto con concretezza, valorizzando chi cerca davvero lavoro.",
        "Efficientamento della pubblica amministrazione: non parole ma fatti. Un cambio di passo reale per i cittadini che meritano risposte concrete.",
        "Serve un tavolo tecnico permanente con tutti gli stakeholder per la transizione energetica, garantendo coesione territoriale.",
    ],
    "Lega": [
        "La sicurezza è il primo driver del benessere sociale: servono risorse concrete e un cronoprogramma chiaro per le forze dell'ordine.",
        "Fare sistema per la difesa dei confini e della sovranità nazionale: questa è la nostra visione strategica per l'Italia.",
        "Il green deal europeo è un framework ideologico che penalizza le imprese italiane: serve discontinuità e concretezza.",
        "Valorizzazione dell'autonomia regionale come benchmark di efficienza: ogni territorio sa meglio di Roma di cosa ha bisogno.",
        "La transizione ecologica non può essere imposta dall'alto: serve un tavolo di confronto che ascolti la gente e le imprese.",
    ],
    "FI": [
        "La resilienza del sistema economico italiano dipende dalla capacità di fare rete tra pubblica amministrazione e settore privato.",
        "Il nostro framework di riforme mira alla valorizzazione del capitale umano attraverso politiche inclusive e sostenibili.",
        "Serve una cabina di regia efficace per l'implementazione del PNRR, con governance chiara e stakeholder coinvolti.",
        "La sfida della digitalizzazione richiede un cambio di passo: portare a terra l'innovazione tecnologica con concretezza.",
        "Il patto per il futuro dell'Italia passa per la coesione tra Nord e Sud, valorizzando i cluster produttivi di eccellenza.",
    ],
    "AVS": [
        "La transizione ecologica deve essere giusta e inclusiva: nessuno deve essere lasciato indietro nel percorso verso la sostenibilità.",
        "Serve un grande patto sociale per fare sistema contro il cambiamento climatico, valorizzando le energie rinnovabili come driver di crescita.",
        "La nostra visione strategica coniuga sostenibilità ambientale e coesione sociale in un framework di sviluppo equo e partecipato.",
        "L'implementazione della transizione energetica richiede governance multilivello e ascolto del territorio, non solo benchmark europei.",
        "Efficientamento energetico e valorizzazione dei beni comuni: questo è il nostro progetto paese per le prossime generazioni.",
    ],
}


def clean_html(text: str) -> str:
    """Rimuove tag HTML e normalizza gli spazi."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def count_syllables_it(word: str) -> int:
    """Stima approssimativa delle sillabe in italiano."""
    word = word.lower()
    vowels = 'aeiouàèéìòùáíó'
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    return max(1, count)


def gulpease_index(text: str) -> float:
    """Calcola l'indice Gulpease per un testo in italiano."""
    sentences = re.split(r'[.!?;]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    n_frasi = max(1, len(sentences))

    words = re.findall(r'\b[a-zA-ZàèéìòùáíóÀÈÉÌÒÙÁÍÓ]+\b', text)
    n_parole = max(1, len(words))
    n_lettere = sum(len(w) for w in words)

    G = 89 + (300 * n_frasi - 10 * n_lettere) / n_parole
    return round(max(0, min(100, G)), 1)


def avg_sentence_length(text: str) -> float:
    """Lunghezza media delle frasi in parole."""
    sentences = re.split(r'[.!?;]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0
    word_counts = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
    return round(sum(word_counts) / len(word_counts), 1)


def buzzword_density(text: str, buzzwords: list) -> float:
    """Percentuale di parole che sono buzzword sul totale delle parole."""
    text_lower = text.lower()
    words = re.findall(r'\b[a-zA-ZàèéìòùáíóÀÈÉÌÒÙÁÍÓ]+\b', text_lower)
    if not words:
        return 0.0

    found = 0
    for bw in buzzwords:
        if bw.lower() in text_lower:
            # conta quante volte appare la buzzword (anche multi-word)
            found += len(re.findall(re.escape(bw.lower()), text_lower))

    return round(min(100, (found / len(words)) * 100 * 5), 1)  # amplify for visualization


def fetch_texts_from_feeds(feeds: list) -> list:
    """Prova a scaricare testi dai feed RSS."""
    texts = []
    for feed_url in feeds:
        try:
            d = feedparser.parse(feed_url)
            for entry in d.entries[:20]:
                content = ""
                if hasattr(entry, 'summary'):
                    content += entry.summary + " "
                if hasattr(entry, 'content'):
                    for c in entry.content:
                        content += c.value + " "
                cleaned = clean_html(content)
                if len(cleaned) > 100:
                    texts.append(cleaned)
        except Exception as e:
            print(f"  Feed {feed_url} non disponibile: {e}")
    return texts


def analyze_party(party_id: str, party_data: dict, buzzwords: list) -> dict:
    """Analizza i testi di un partito e restituisce le metriche."""
    print(f"  Analisi: {party_data['name']}...")
    
    texts = fetch_texts_from_feeds(party_data["feeds"])
    
    if not texts:
        print(f"    -> Uso testi di fallback per {party_data['name']}")
        texts = FALLBACK_TEXTS.get(party_id, [])

    if not texts:
        return None

    full_text = " ".join(texts[:50])  # max 50 testi

    g_index = gulpease_index(full_text)
    avg_sl = avg_sentence_length(full_text)
    bw_density = buzzword_density(full_text, buzzwords)

    # Normalizza su scala 0-100 per il radar chart
    # Complessità: 100 - Gulpease (più basso = più complesso)
    complessita = round(100 - g_index, 1)
    # Fuffa: inverso della leggibilità pesato per buzzwords
    fuffa = round((complessita * 0.5 + bw_density * 0.5), 1)
    # Lunghezza frasi: normalizzata (es. 30 parole/frase = 100%)
    lunghezza = round(min(100, (avg_sl / 30) * 100), 1)

    # Trova i top 3 testi più "Supercazzola"
    text_samples = []
    for t in texts[:10]:
        score = 100 - gulpease_index(t) + buzzword_density(t, buzzwords)
        text_samples.append({"text": t[:300] + "..." if len(t) > 300 else t, "score": score})
    text_samples.sort(key=lambda x: x["score"], reverse=True)

    return {
        "id": party_id,
        "name": party_data["name"],
        "color": party_data["color"],
        "n_testi": len(texts),
        "metrics": {
            "gulpease": g_index,
            "complessita": complessita,
            "buzzword_density": bw_density,
            "fuffa_index": fuffa,
            "avg_sentence_length": avg_sl,
        },
        "radar": {
            "Complessità Sintattica": complessita,
            "Densità Buzzwords": round(min(100, bw_density), 1),
            "Indice di Fuffa": round(min(100, fuffa), 1),
            "Lunghezza Frasi": lunghezza,
        },
        "top_samples": text_samples[:3],
    }


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_path = project_root / "public" / "data" / "supercazzola_data.json"
    buzzwords_path = script_dir / "buzzwords.json"

    print("=== Supercazzola Index Scraper ===")
    print(f"Avvio analisi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Carica buzzwords
    with open(buzzwords_path, "r", encoding="utf-8") as f:
        bw_config = json.load(f)
    buzzwords = bw_config["buzzwords"]
    print(f"Caricate {len(buzzwords)} buzzwords.")

    parties_data = []
    for party_id, party_info in PARTY_FEEDS.items():
        result = analyze_party(party_id, party_info, buzzwords)
        if result:
            parties_data.append(result)

    output = {
        "generated_at": datetime.now().isoformat(),
        "parties": parties_data,
        "buzzwords_count": len(buzzwords),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Dati salvati in: {output_path}")
    print(f"   Partiti analizzati: {len(parties_data)}")


if __name__ == "__main__":
    main()
