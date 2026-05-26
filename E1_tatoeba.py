#!/usr/bin/env python3
"""
fetch_tatoeba.py
----------------
Lit verbs_data.json, extrait toutes les formes conjuguées espagnoles,
interroge l'API Tatoeba, et génère :
  - index.json (progressif + reprise)
  - index.html
  - state.json (checkpoint reprise)
"""

import json
import time
import argparse
import sys
import ssl
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# ─── Configuration ───────────────────────────────────────────────────────────
TATOEBA_API   = "https://api.tatoeba.org/v1/sentences"
AUDIO_PATTERN = "https://audio.tatoeba.org/sentences/spa/{id}.mp3"
SLEEP_BETWEEN = 0.1
MAX_PAGES     = 30

ssl_context = ssl._create_unverified_context()
# ─────────────────────────────────────────────────────────────────────────────


def load_verbs(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return raw.get("verbs_db", raw)


def extract_forms(verbs_db: dict) -> list[dict]:
    forms = []
    for verb, moods in verbs_db.items():
        for mood, tenses in moods.items():
            for tense, conjugations in tenses.items():
                for conj in conjugations:
                    es = conj.get("es", "").strip()
                    if es:
                        forms.append({
                            "verb": verb,
                            "mood": mood,
                            "tense": tense,
                            "pronoun": conj.get("pronoun", ""),
                            "fr": conj.get("fr", ""),
                            "es": es,
                        })
    return forms


# ─── STATE (reprise) ────────────────────────────────────────────────────────

def load_state(state_path: Path) -> set:
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_state(state_path: Path, done: set):
    tmp = list(done)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(tmp, f, ensure_ascii=False)


# ─── JSON progressif (append sécurisé) ──────────────────────────────────────

def append_json(path: Path, entries: list[dict]):
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

    with open(path, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data.extend(entries)
        f.seek(0)
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.truncate()


# ─── API Tatoeba ────────────────────────────────────────────────────────────

def fetch_sentences(query: str, limit: int | None = None) -> list[dict]:
    params = {
        "q": "=" + query,
        "lang": "spa",
        "has_audio": "yes",
        "trans:lang": "fra",
        "sort": "random",
    }

    url = f"{TATOEBA_API}?{urlencode(params)}"
    print(f"[API] {query} -> {url}")

    sentences = []
    page = 0

    while url and page < MAX_PAGES:
        page += 1
        print ("page:",page)
        try:
            req = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "TatoebaFetcher/1.0",
                },
            )
            with urlopen(req, timeout=15, context=ssl_context) as resp:
                body = json.loads(resp.read().decode("utf-8"))

        except (HTTPError, URLError) as e:
            print(f"⚠ erreur réseau: {e}", file=sys.stderr)
            break

        for sent in body.get("data", []):
            fra_text = next(
                (
                    t.get("text", "") or ""
                    for t in sent.get("translations", [])
                    if isinstance(t, dict) and t.get("lang") == "fra" and t.get("text")
                ),
                "",
            )

            audios = sent.get("audios", [])
            audio_url = AUDIO_PATTERN.format(id=sent["id"])
            audio_author = audios[0].get("author", "") if audios else ""

            sentences.append({
                "id": sent["id"],
                "es_text": sent.get("text", ""),
                "fr_text": fra_text,
                "audio_url": audio_url,
                "audio_author": audio_author,
                "license": sent.get("license", ""),
                "owner": sent.get("owner", ""),
            })

            if limit and len(sentences) >= limit:
                return sentences

        paging = body.get("paging", {})
        url = paging.get("next") if paging.get("has_next") else None

        time.sleep(SLEEP_BETWEEN)

    return sentences



# ─── BUILD INCREMENTAL ──────────────────────────────────────────────────────

def build_index(verbs_db: dict, out_dir: Path, limit: int | None = None):
    forms = extract_forms(verbs_db)

    print(f"{len(forms)} formes trouvées")

    seen_es = {}
    for f in forms:
        seen_es.setdefault(f["es"], []).append(f)

    state_path = out_dir / "state.json"
    json_path  = out_dir / "index.json"

    done = load_state(state_path)

    total = len(seen_es)

    for i, (es_form, meta_list) in enumerate(seen_es.items(), 1):

        if es_form in done:
            continue

        print(f"[{i}/{total}] {es_form}")

        sents = fetch_sentences(es_form, limit)

        batch = []

        for sent in sents:
            for meta in meta_list:
                batch.append({
                    "id": sent["id"],
                    "es_text": sent["es_text"],
                    "fr_text": sent["fr_text"],
                    "audio_url": sent["audio_url"],
               #     "audio_author": sent["audio_author"],
               #     "license": sent["license"],
               #     "owner": sent["owner"],
                    "verb": meta["verb"],
                    "mood": meta["mood"],
                    "tense": meta["tense"],
                    "pronoun": meta["pronoun"],
                    "conj_fr": meta["fr"],
                    "conj_es": meta["es"],
                })

        if batch:
            append_json(json_path, batch)

        done.add(es_form)
        save_state(state_path, done)

    return json_path


# ─── HTML (reconstruit depuis JSON) ─────────────────────────────────────────

def save_html(index_path: Path, out_path: Path):
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    by_verb = {}
    for e in index:
        by_verb.setdefault(e["verb"], {}).setdefault(e["mood"], {}).setdefault(e["tense"], []).append(e)

    rows = []

    for verb, moods in sorted(by_verb.items()):
        for mood, tenses in moods.items():
            for tense, entries in tenses.items():
                for e in entries:
                    audio = (
                        f'<audio controls preload="none" src="{e["audio_url"]}">'
                        f'Your browser does not support the audio element.</audio>'
                        if e["audio_url"] else "—"
                    )

                    rows.append(f"""
<tr>
  <td><strong>{e['verb']}</strong></td>
  <td>{e['mood']}</td>
  <td>{e['tense']}</td>
  <td>{e['pronoun']}</td>
  <td>{e['es_text']}</td>
  <td>{e['fr_text'] or '—'}</td>
  <td>{audio}</td>
  <td><small>{e['conj_es']} / {e['conj_fr']}</small></td>
</tr>
""")

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Tatoeba</title>
</head>
<body>
  <table border="1" style="border-collapse: collapse;">
    <thead>
      <tr>
        <th>Vérb</th>
        <th>Humeur</th>
        <th>Temps</th>
        <th>Pronom</th>
        <th>Phrase ESP</th>
        <th>Phrase FR</th>
        <th>Audio</th>
        <th>Conjugaison</th>
      </tr>
    </thead>
    <tbody>
{''.join(rows)}
    </tbody>
  </table>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="verbs_data.json")
    parser.add_argument("--out", default=".")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    verbs_db = load_verbs(args.file)

    index_path = build_index(verbs_db, out_dir, limit=args.limit)

    if not args.json_only:
        save_html(index_path, out_dir / "indexphrase.html")

    print("Terminé")


if __name__ == "__main__":
    main()
