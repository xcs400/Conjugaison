import csv
import json

data = []

# Lecture CSV
with open("export.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(
        f,
        delimiter=";"
    )

    for row in reader:
        # Conversion types
        row["id"] = int(row["id"])
        row["valid"] = int(row["valid"])

        data.append(row)

# Sauvegarde JSON
with open("flag_1.json", "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        ensure_ascii=False,
        indent=2
    )

print("Import terminé : import.json")
