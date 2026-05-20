import json
import re

def last_word(text):
    words = re.findall(r"\w+", text.lower())
    return words[-1] if words else ""

def normalize(text):
    return text.lower()

def is_valid(item):
    fr_text = normalize(item.get("fr_text", ""))
    conj_fr = normalize(item.get("conj_fr", ""))
    word = last_word(conj_fr)
    words_in_text = set(re.findall(r"\w+", fr_text))
    valid = 1 if word in words_in_text else 0
  #  print(f"[CHECK] id={item.get('id')} | mot='{word}' | valid={valid}")
    return valid

print("[START] lecture index.json")
with open("index.json", "r", encoding="utf-8") as f:
    data = json.load(f)
print(f"[INFO] {len(data)} éléments chargés")

# ── Suppression Impératif + ustedes / usted / nosotros ──────────────────────
EXCLUDED_PRONOUNS = {"ustedes", "usted", "nosotros"}
before = len(data)
data = [
    item for item in data
    if not (
        item.get("mood") == "Impératif"
        and item.get("pronoun") in EXCLUDED_PRONOUNS
    )
]
print(f"[FILTER] {before - len(data)} éléments supprimés → {len(data)} restants")
# ────────────────────────────────────────────────────────────────────────────

# ── Détection et suppression des doublons sur "id" (garde le premier) ───────
##seen_ids = {}        # id → (index, item)
##duplicates = []
##deduplicated = []
##
##for idx, item in enumerate(data):
##    item_id = item.get("id")
##    if item_id in seen_ids:
##        duplicates.append({
##            "id":            item_id,
##            "premier_index": seen_ids[item_id][0],
##            "premier_item":  seen_ids[item_id][1],
##            "doublon_index": idx,
##            "doublon_item":  item,
##        })
##    else:
##        seen_ids[item_id] = (idx, item)
##        deduplicated.append(item)
##
##if duplicates:
##    sep = "─" * 60
##    print(f"\n[DOUBLONS] {len(duplicates)} doublon(s) détecté(s)")
##    for d in duplicates:
##        print(f"\n{sep}")
##        print(f"  ID            : {d['id']}")
##        print(f"  ┌─ PREMIER  (index {d['premier_index']})")
##        for k, v in d["premier_item"].items():
##            print(f"  │  {k:<20}: {v}")
##        print(f"  └─ DOUBLON  (index {d['doublon_index']}) → ignoré")
##        for k, v in d["doublon_item"].items():
##            print(f"     {k:<20}: {v}")
##    print(f"\n{sep}")
##else:
##    print("[DOUBLONS] aucun doublon détecté")
##
##print(f"[DEDUP] {len(data) - len(deduplicated)} supprimé(s) → {len(deduplicated)} restants\n")
##
##data = deduplicated
# ────────────────────────────────────────────────────────────────────────────

print("[PROCESS] début validation")
for i, item in enumerate(data, start=1):
  #  print(f"[ITEM {i}/{len(data)}] id={item.get('id')}")
    item["valid"] = 1 # is_valid(item)


print("[WRITE] écriture resultat.json")
with open("resultat.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("[DONE] traitement terminé")


print("[WRITE] écriture flag_2.json")
data_flag_2 = [item for item in data if item.get("valid") == 0]

with open("flag_2.json", "w", encoding="utf-8") as f:
    json.dump(data_flag_2, f, ensure_ascii=False, indent=2)
print(f"[DONE] {len(data_flag_2)} éléments avec valid=0")




print("[WRITE] écriture flag_1.json")
data_flag_1 = [item for item in data if item.get("valid") == 1]

with open("flag_1.json", "w", encoding="utf-8") as f:
    json.dump(data_flag_1, f, ensure_ascii=False, indent=2)
print(f"[DONE] {len(data_flag_1)} éléments avec valid=1")


data=data_flag_1
# ── Détection et suppression des doublons sur "id" (garde le premier) ───────
seen_ids = {}        # id → (index, item)
duplicates = []
deduplicated = []

for idx, item in enumerate(data):
    item_id = item.get("id")
    if item_id in seen_ids:
        duplicates.append({
            "id":            item_id,
            "premier_index": seen_ids[item_id][0],
            "premier_item":  seen_ids[item_id][1],
            "doublon_index": idx,
            "doublon_item":  item,
        })
    else:
        seen_ids[item_id] = (idx, item)
        deduplicated.append(item)

if duplicates:
    sep = "─" * 60
    print(f"\n[DOUBLONS] {len(duplicates)} doublon(s) détecté(s)")

    for d in duplicates:
        print(f"\n{sep}")
        print(f"  ID   : {d['id']}")
  
        print(f"{'es':<20}: {d['premier_item']['es_text']}")   # ✅ via premier_item
        print(f"{'fr':<20}: {d['premier_item']['fr_text']}")   # ✅ via premier_item
        print(f"  [{'tense':<20}: {d['premier_item']['tense']},")   # ✅ via premier_item
        print(f" {'pronoun':<20}: {d['premier_item']['pronoun']},")  # ✅ via premier_item
        print(f" {'conj_es':<20}: {d['premier_item']['conj_es']}]")   # ✅ idem
        print(f" {'[tense':<20}: {d['doublon_item']['tense']},")   # ✅ via premier_item
        print(f" {'pronoun':<20}: {d['doublon_item']['pronoun']},")   # ✅ via premier_item
        print(f" {'conj_es':<20}: {d['doublon_item']['conj_es']}]")   # ✅ idem
 
else:
    print("[DOUBLONS] aucun doublon détecté")

    
print(f"[DEDUP] {len(data) - len(deduplicated)} supprimé(s) → {len(deduplicated)} restants\n")




