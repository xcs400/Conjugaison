"""
Script : split_flag2_batches.py

Règles par groupe (mood, tense, verb, pronoun) :

  count <= BATCH_SIZE  → reconduit à l'identique dans TOUS les batches

  count >  BATCH_SIZE  → découpé en tranches de BATCH_SIZE :
    • tranche pleine  → telle quelle
    • tranche partielle (dernière vraie tranche) → complétée avec le
      début du batch précédent pour ce groupe jusqu'à BATCH_SIZE
    • tranche vide (batches suivants) → reconduit le contenu du
      batch précédent pour ce groupe (stabilisation)

Tri final de chaque batch : verb → pronoun → mood → tense
"""

import json
from collections import defaultdict, Counter
from pathlib import Path

INPUT_FILE            = "flag_2.json"
ADDITIONAL_INPUT_FILE = "additional_phases.json"
OUTPUT_PREFIX         = "flag_2_batch"
EXTRA_VERB_FILE       = "extra_verb.json"
BATCH_SIZE            = 10


def load_json_file(path):
    records = []

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))

            except json.JSONDecodeError as e:

                print("\n" + "="*80)
                print("ERREUR JSON")
                print("="*80)

                print(f"Fichier : {path}")
                print(f"Ligne   : {line_no}")
                print(f"Colonne : {e.colno}")
                print(f"Position: {e.pos}")
                print(f"Erreur  : {e.msg}")

                print("\nLigne complète :")
                print(line)

                print("\nPointeur :")
                print(" " * (e.colno - 1) + "^")

                print("\nExtrait autour de l'erreur :")
                start = max(0, e.pos - 60)
                end   = min(len(line), e.pos + 60)
                print(line[start:end])

                raise

    return records

def load_and_merge(main_path, additional_path):
    """Charge main_path, puis fusionne additional_path si présent.
    Les doublons (même id) dans additional sont ignorés."""
    records = load_json_file(main_path)
    existing_ids = {r.get("id") for r in records}

    additional_path = Path(additional_path)
    if additional_path.exists():
        additional = load_json_file(additional_path)
        added = 0
        for r in additional:
            if r.get("id") not in existing_ids:
                records.append(r)
                existing_ids.add(r.get("id"))
                added += 1
        skipped = len(additional) - added
        print(f"  Lecture de : {additional_path}")
        print(f"  {len(additional)} entrées chargées  "
              f"({added} ajoutées, {skipped} doublons ignorés).")
    else:
        print(f"  {additional_path} introuvable — ignoré.")

    return records


def build_batches(records, batch_size, allowed_verbs=None):
    # 0. Filtrer les verbes non listés dans verbs_db (si fourni)
    if allowed_verbs is not None:
        filtered_out = [r for r in records if r.get("verb", "") not in allowed_verbs]
        records      = [r for r in records if r.get("verb", "") in allowed_verbs]
    else:
        filtered_out = []

    # 1. Grouper
    groups = defaultdict(list)
    for rec in records:
        key = (rec.get("mood",""), rec.get("tense",""), rec.get("verb",""), rec.get("pronoun",""))
        groups[key].append(rec)

    # 2. Petits (≤ batch_size) reconduits / grands (> batch_size) découpés
    small = {k: v for k, v in groups.items() if len(v) <= batch_size}
    large = {k: v for k, v in groups.items() if len(v) >  batch_size}

    # 3. Nombre de batches = nb de tranches du plus grand groupe
    if large:
        max_batches = max(
            (len(v) + batch_size - 1) // batch_size for v in large.values()
        )
    else:
        max_batches = 1

    # 4. Mémoire du contenu du batch précédent pour chaque grand groupe
    prev = {}   # key → liste des phrases retenues au batch précédent

    batches = []
    for idx in range(max_batches):
        batch = []

        # Petits groupes → toujours complets
        for phrases in small.values():
            batch.extend(phrases)

        # Grands groupes
        start = idx * batch_size
        end   = start + batch_size

        for key, phrases in large.items():
            new_slice = phrases[start:end]

            if not new_slice:
                # Plus rien de nouveau → reconduire le batch précédent
                result = prev[key]

            elif len(new_slice) < batch_size:
                # Tranche incomplète → compléter depuis le batch précédent
                needed  = batch_size - len(new_slice)
                filler  = prev.get(key, phrases[:batch_size])
                padding = filler[:needed]
                result  = new_slice + padding

            else:
                # Tranche pleine
                result = new_slice

            prev[key] = result
            batch.extend(result)

        # Tri final
        batch.sort(key=lambda r: (
            r.get("verb",    ""),
            r.get("pronoun", ""),
            r.get("mood",    ""),
            r.get("tense",   ""),
        ))

        # Dédoublonnage par id (même phrase dans deux groupes distincts)
        seen_ids = set()
        deduped  = []
        for r in batch:
            rid = r.get("id")
            if rid not in seen_ids:
                seen_ids.add(rid)
                deduped.append(r)
        batches.append(deduped)

    return batches, len(small), len(large), filtered_out


def save_jsonl(records, path):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ── Rapport récapitulatif ────────────────────────────────────────────────────

def load_verbs_db(path="verbs_data.json"):
    data = json.load(open(path, encoding="utf-8"))
    return data["verbs_db"]


def generate_recap(records, verbs_db, output_path="flag_2_recap.json"):
    """
    Pour chaque verbe de verbs_db :
      - pour chaque combinaison (mood, tense, pronoun) attendue :
          → compte de phrases dans flag_2.json
          → MANQUANT si 0
    Verbes hors verbs_db → listés séparément.
    """
    counts = Counter()
    verbs_in_data = set()
    for r in records:
        key = (r.get("verb",""), r.get("mood",""), r.get("tense",""), r.get("pronoun",""))
        counts[key] += 1
        verbs_in_data.add(r.get("verb",""))

    known_verbs = set(verbs_db.keys())
    extra_verbs = sorted(verbs_in_data - known_verbs)

    recap = {}
    for verb, moods in verbs_db.items():
        recap[verb] = {}
        for mood, tenses in moods.items():
            recap[verb][mood] = {}
            for tense, pronouns in tenses.items():
                recap[verb][mood][tense] = {}
                for p_entry in pronouns:
                    pronoun = p_entry["pronoun"]
                    cnt = counts.get((verb, mood, tense, pronoun), 0)
                    recap[verb][mood][tense][pronoun] = cnt if cnt > 0 else "MANQUANT"

    result = {
        "recap_par_verbe": recap,
        "verbes_hors_verbs_db": extra_verbs,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Affichage console résumé
    print(f"\n  {'─'*58}")
    print(f"  RAPPORT RÉCAPITULATIF → {output_path}")
    print(f"  {'─'*58}")
    total_missing = 0
    for verb, moods in recap.items():
        missing = []
        for mood, tenses in moods.items():
            for tense, pronouns in tenses.items():
                for pronoun, val in pronouns.items():
                    if val == "MANQUANT":
                        missing.append(f"{mood}/{tense}/{pronoun}")
        status = f"{len(missing)} manquant(s)" if missing else "complet ✓"
        print(f"  {verb:<12}  {status}")
        total_missing += len(missing)
    if extra_verbs:
        print(f"\n  Verbes hors verbs_db ({len(extra_verbs)}) :")
        for v in extra_verbs:
            print(f"    - {v}")
    print(f"\n  Total combinaisons manquantes : {total_missing}")
    print(f"  {'─'*58}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'─'*62}")
    print(f"  Lecture de : {INPUT_FILE}")
    records = load_and_merge(INPUT_FILE, ADDITIONAL_INPUT_FILE)
    print(f"  Total fusionné : {len(records)} entrées.")

    # Charger verbs_db pour filtrer ET pour le rapport
    try:
        verbs_db      = load_verbs_db("verbs_data.json")
        allowed_verbs = set(verbs_db.keys())
        print(f"  Verbes autorisés (verbs_db)  : {len(allowed_verbs)}")
    except FileNotFoundError:
        verbs_db      = None
        allowed_verbs = None
        print("  verbs_data.json introuvable — aucun filtre appliqué.")

    batches, n_small, n_large, filtered_out = build_batches(
        records, BATCH_SIZE, allowed_verbs=allowed_verbs
    )

    # Sauvegarde des phrases filtrées dans extra_verb.json
    if filtered_out:
        filtered_out.sort(key=lambda r: (
            r.get("verb",    ""),
            r.get("pronoun", ""),
            r.get("mood",    ""),
            r.get("tense",   ""),
        ))
        save_jsonl(filtered_out, EXTRA_VERB_FILE)
        print(f"  Entrées filtrées (hors db)   : {len(filtered_out)}  → {EXTRA_VERB_FILE}")
    else:
        print(f"  Entrées filtrées (hors db)   : 0  (aucun fichier créé)")

    print(f"  Groupes reconduits (≤{BATCH_SIZE}) : {n_small}")
    print(f"  Groupes découpés   (> {BATCH_SIZE}) : {n_large}")
    print(f"  → {len(batches)} fichier(s) à générer\n")

    print(f"  {'Fichier':<32}  {'Phrases':>7}")
    print(f"  {'─'*40}")
    for i, batch in enumerate(batches, 1):
        out = f"{OUTPUT_PREFIX}_{i}.json"
        save_jsonl(batch, out)
        print(f"  {out:<32}  {len(batch):>7}")
    if filtered_out:
        print(f"  {EXTRA_VERB_FILE:<32}  {len(filtered_out):>7}")
    print(f"  {'─'*40}")

    # Rapport récapitulatif (sur records bruts → MANQUANT visible même si filtré)
    if verbs_db is not None:
        generate_recap(records, verbs_db)
    else:
        print("  verbs_data.json introuvable — rapport ignoré.")

    print(f"  Taille de référence (batch 1) : {len(batches[0])}")
    print(f"{'─'*62}\n")
