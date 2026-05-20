import json
import csv

# Charger le JSON
with open("flag_1.json", "r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    raise ValueError("Le JSON est vide")

# Colonnes
fieldnames = data[0].keys()

# Export CSV
with open("export.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
        delimiter=";"
    )

    writer.writeheader()
    writer.writerows(data)

print("Export terminé : export.csv")
