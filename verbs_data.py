import json
import os

JSON_PATH = os.path.join(os.path.dirname(__file__), "verbs_data.json")

with open(JSON_PATH, "r", encoding="utf-8") as f:
    _data = json.load(f)

HINTS = _data["hints"]
VERBS_DB = _data["verbs_db"]

def get_hint(mode, tense, pronoun_idx):
    try:
        return HINTS[mode][tense][pronoun_idx]
    except (KeyError, IndexError):
        return ""
