# -*- coding: utf-8 -*-
"""Audit every achievement row: text hygiene, attribution, rewards, difficulty."""
import json, re, sys, io
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")

d = json.load(open("payday/data/app_final.json", encoding="utf-8"))
A = d["achievements"]
heists = {h["page"]: h for h in d["heists"]}
labels = d["category_labels"]

MARKUP = [
    ("wikilink", r"\[\[|\]\]"),
    ("template", r"\{\{|\}\}"),
    ("pipe", r"\|"),
    ("bold", r"'{2,}"),
    ("tag", r"<[^>]+>"),
    ("color", r"\bcolor\s*\|"),
    ("nbsp", r"&nbsp;| "),
    ("ellipsis_trunc", r"[«\"]?\s*\.{3}\s*$"),
]
DIFFS = ["easy", "normal", "hard", "very hard", "overkill", "mayhem",
         "death wish", "below zero", "death sentence"]
RU_DIFFS = {"Нормально": "normal", "Сложно": "hard", "Очень сложно": "very hard",
            "OVERKILL": "overkill", "Хаос": "mayhem", "Жажда смерти": "death wish",
            "Смертный приговор": "death sentence", "Смертельный приговор": "death sentence",
            "Ниже нуля": "below zero", "Легко": "easy"}

issues = defaultdict(list)

for a in A:
    nm, ds = a["name"], a.get("desc") or ""
    dsn = a.get("desc_ru") or ""
    tag = f"{nm[:44]}"

    for label, pat in MARKUP:
        if re.search(pat, ds):
            issues["мусор в EN"].append((tag, ds[:90]))
        if re.search(pat, dsn):
            issues["мусор в RU"].append((tag, dsn[:90]))

    if not a.get("name_ru"):
        issues["нет названия RU"].append((tag, ds[:70]))
    if not dsn:
        issues["нет описания RU"].append((tag, ds[:70]))

    # difficulty mentioned but never captured
    found = set()
    for x in DIFFS:
        if re.search(r"(?<![a-z])" + re.escape(x) + r"(?![a-z])", ds.lower()):
            found.add(x)
    for ru, en in RU_DIFFS.items():
        if ru in dsn:
            found.add(en)
    missing = found - set(a.get("difficulties") or [])
    if missing:
        issues["сложность не извлечена"].append((tag, "в тексте: " + ", ".join(sorted(missing))))

    # rewards stated in the text but not extracted
    if re.search(r"[Uu]nlocks?\b", ds) and not a.get("rewards"):
        issues["награда в тексте, не извлечена"].append((tag, ds[-110:]))

print("=" * 72)
print("АУДИТ", len(A), "достижений")
print("=" * 72)
total = 0
for k in sorted(issues, key=lambda x: -len(issues[x])):
    v = issues[k]
    total += len(v)
    print(f"\n### {k} — {len(v)}")
    for tag, ex in v[:8]:
        print(f"    {tag:46s} {ex}")
    if len(v) > 8:
        print(f"    …ещё {len(v)-8}")
print(f"\nВСЕГО ЗАМЕЧАНИЙ: {total}")

# structure sanity
print("\n" + "=" * 72)
print("СТРУКТУРА")
print("=" * 72)
print("дублей названий:", len(A) - len({a["name"].lower() for a in A}))
print("без единой награды:", sum(1 for a in A if not a.get("rewards")))
print("без иконки:", sum(1 for a in A if not a.get("img")) if "img" in A[0] else "н/д")
print("категории:", Counter(a["category"] for a in A).most_common())
print("с пометкой дня:", sum(1 for a in A if a.get("day")))
print("помечено выполненным:", len(d.get("done_ids", [])))

# which heists have suspiciously low or zero achievement counts
print("\nхостов с 0 достижений:", [h["name"] for h in d["heists"] if not h["ids"]])
low = sorted((h for h in d["heists"] if 0 < len(h["ids"]) <= 2),
             key=lambda h: len(h["ids"]))
print("хостов с 1-2 достижениями:", [(h["name"], len(h["ids"])) for h in low])