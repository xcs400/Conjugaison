#!/usr/bin/env python3

import json
import re
import time
import argparse
import logging

from pathlib import Path
from collections import Counter

import requests
from tqdm import tqdm

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

OLLAMA_API_KEY = "d3af6ab0dcb443d7b5a835eb98507668.jVVYaoWogoypxTioDyJePKxx"
OLLAMA_BASE_URL = "https://api.ollama.com"
MODEL_NAME = "gemma4:31b"

DEFAULT_INPUT = "simplephase.json"
DEFAULT_OUTPUT = "flag_2.json"

SLEEP_BETWEEN = 0.3
MAX_RETRIES = 3

DEBUG = True

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """
Tu es un expert en linguistique espagnole et française.

Tu dois analyser la phrase espagnole.

IMPORTANT :
- Si la phrase contient plusieurs verbes conjugués :
  retourne un TABLEAU JSON avec un objet par verbe.
- Si la phrase contient un seul verbe :
  retourne un tableau avec un seul objet.
- Réponse JSON UNIQUEMENT.
- Aucun texte hors JSON.
- JSON valide obligatoire.

Tu DOIS utiliser UNIQUEMENT ces valeurs :

mood :
- Indicatif
- Subjonctif
- Conditionnel
- Impératif

tense :
- Présent
- Passé composé
- Prétérit
- Imparfait
- Plus-que-parfait
- Futur simple
- Futur antérieur
- Affirmatif


pronoun :
- yo
- tú
- 3SI      <- (use this for él/ella/usted)
- nosotros
- vosotros <- (use this for vosotros/vosotras)
- 3PL      <- (use this for ellos/ellas/ustedes)


Realpronoun :
- yo
- tú
- él
- ella
- usted
- imp-3SI
- nosotros
- vosotros
- ellas
- ellos
- ustedes
- imp-3PL

Règles :
- "verb" doit être à l'infinitif.
- "conj_es" doit contenir uniquement la conjugaison exacte trouvée.
- "conj_fr" doit être la traduction française exacte du verbe conjugué.
- "fr_text" = traduction complète de la phrase.
- Conserve les accents.
- audio_url doit être recopié.

Format obligatoire :

[
  {
    "id": 204,
    "es_text": "Te he comprado un lápiz.",
    "mood": "Indicatif",
    "tense": "Passé composé",
    "verb": "comprar",
    "pronoun": "yo",
    "Realpronoun": "yo",
    "fr_text": "Je t'ai acheté un crayon.",
    "audio_url": "https://audio.tatoeba.org/test.mp3",
    "conj_fr": "ai acheté",
    "conj_es": "he comprado"
  }
]
"""

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

def build_prompt(record: dict) -> str:
    return f"""
Phrase espagnole :
{record.get('es_text', '')}

Audio URL :
{record.get('audio_url', '')}

ID :
{record.get('id', '')}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# STRIP MARKDOWN FENCES
# ═══════════════════════════════════════════════════════════════════════════════

def strip_markdown_fences(text: str) -> str:
    text = text.strip()

    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)

    return text.strip()

# ═══════════════════════════════════════════════════════════════════════════════
# API CALL
# ═══════════════════════════════════════════════════════════════════════════════

def call_ollama(record: dict):

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_prompt(record),
            },
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 1500,
        }
    }

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    if DEBUG:
        print("\n" + "=" * 80)
        print(f"ID      : {record.get('id')}")
        print(f"MODEL   : {MODEL_NAME}")
        print("-" * 80)
        print(build_prompt(record))
        print("-" * 80)

    start = time.time()

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        headers=headers,
        json=payload,
        timeout=120,
    )

    elapsed = round(time.time() - start, 2)

    if DEBUG:
        print(f"STATUS  : {response.status_code}")
        print(f"LATENCE : {elapsed}s")
        print("-" * 80)

    if response.status_code != 200:
        if DEBUG:
            print(response.text)

        raise Exception(f"{response.status_code} - {response.text}")

    data = response.json()

    if DEBUG:
        print("REPONSE BRUTE :")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("-" * 80)

    content = data["message"]["content"]

    content_clean = strip_markdown_fences(content)

    if DEBUG:
        print("CONTENU (nettoyé) :")
        print(content_clean)
        print("=" * 80)

    parsed = json.loads(content_clean)

    if not isinstance(parsed, list):
        raise Exception("Le modèle doit retourner une LISTE JSON")

    allowed_moods = {
        "Indicatif",
        "Subjonctif",
        "Conditionnel",
        "Impératif",
    }

    allowed_tenses = {
        "Présent",
        "Passé composé",
        "Prétérit",
        "Imparfait",
        "Plus-que-parfait",
        "Futur simple",
        "Futur antérieur",
        "Affirmatif",
    }

    allowed_pronouns = {
        "yo",
        "tú",
        "3SI",
        "nosotros",
        "vosotros",
        "3PL",
    }

    allowed_realpronouns = {
        "yo",
        "tú",
        "él",
        "ella",
        "usted",
        "imp-3SI",
        "nosotros",
        "vosotros",
        "ellas",
        "ellos",
        "ustedes",
        "imp-3PL",
    }

    validated = []

    for item in parsed:

        if item.get("mood") not in allowed_moods:
            raise Exception(f"Mood invalide : {item.get('mood')}")

        if item.get("tense") not in allowed_tenses:
            raise Exception(f"Tense invalide : {item.get('tense')}")

        if item.get("pronoun") not in allowed_pronouns:
            raise Exception(f"Pronoun invalide : {item.get('pronoun')}")

        if item.get("Realpronoun") not in allowed_realpronouns:
            raise Exception(f"Realpronoun invalide : {item.get('Realpronoun')}")

        validated.append(item)

    return validated

# ═══════════════════════════════════════════════════════════════════════════════
# RETRY
# ═══════════════════════════════════════════════════════════════════════════════

def ask_llm(record):

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            return call_ollama(record)

        except Exception as e:

            log.warning(
                "ID %s - tentative %d - %s",
                record.get("id"),
                attempt,
                e,
            )

            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    return []

# ═══════════════════════════════════════════════════════════════════════════════
# LOAD DONE IDS
# ═══════════════════════════════════════════════════════════════════════════════

def load_done_ids(output_path: Path):

    done = set()

    if not output_path.exists():
        return done

    with output_path.open("r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                obj = json.loads(line)

                if "id" in obj:
                    done.add(obj["id"])

            except Exception:
                pass

    return done

# ═══════════════════════════════════════════════════════════════════════════════
# WRITE RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

def write_results(output_path: Path, results: list):

    with output_path.open("a", encoding="utf-8") as f:

        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

        f.flush()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RUN
# ═══════════════════════════════════════════════════════════════════════════════

def run(input_path: Path, output_path: Path):

    with input_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    done = load_done_ids(output_path)

    log.info("%d phrases déjà traitées", len(done))

    todo = [r for r in records if r.get("id") not in done]

    log.info("%d phrases restantes", len(todo))

    SER_ESTAR_FORMS = {
        # ser
        "soy","eres","estaban" 

    }

    verb_counter = Counter(SER_ESTAR_FORMS)

    def rebuild_pattern():
        return re.compile(
            r"\b(" + "|".join(map(re.escape, verb_counter.keys())) + r")\b",
            re.IGNORECASE
        )

    pattern = rebuild_pattern()

    for record in tqdm(todo, desc="Traitement", unit="phrase"):

        es_text = record.get("es_text", "")

        if pattern.search(es_text):
            print("skip", es_text)
            continue

        results = ask_llm(record)

        # ─────────────────────────────────────────────────────────────
        # ajoute automatiquement les verbes fréquents au pattern
        # ─────────────────────────────────────────────────────────────

        for item in results:

            conj = item.get("conj_es", "").strip().lower()

            if not conj:
                continue

            words = re.findall(
                r"\b[\wáéíóúüñ]+\b",
                conj,
                flags=re.IGNORECASE
            )

            for word in words:

                verb_counter[word] += 1

                if verb_counter[word] > 10:

                    print(f"[AUTO-ADD] {word}")

                    pattern = rebuild_pattern()

        if results:
            write_results(output_path, results)

        time.sleep(SLEEP_BETWEEN)

# ═══════════════════════════════════════════════════════════════════════════════
# CLEAN DUPLICATES
# ═══════════════════════════════════════════════════════════════════════════════

def clean_duplicates():

    input_path = Path("flag_2.json")
    output_path = Path("flag_2_clean.json")

    seen = set()
    cleaned = []

    for line in input_path.read_text(encoding="utf-8").splitlines():

        line = line.strip()

        if not line:
            continue

        try:
            obj = json.loads(line)

            key = (obj.get("id"), obj.get("verb"))

            if key not in seen:
                seen.add(key)
                cleaned.append(obj)

        except Exception as e:
            print(f"Ligne invalide ignorée : {e}")

    with output_path.open("w", encoding="utf-8") as f:

        for obj in cleaned:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"{len(cleaned)} entrées écrites.")

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)

    args = parser.parse_args()

    run(Path(args.input), Path(args.output))
