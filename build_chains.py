# -*- coding: utf-8 -*-
"""Resolve where each required mask actually comes from, and mark real chains."""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

A = json.load(open("payday/data/app_data.json", encoding="utf-8"))["achievements"]

# 1) every achievement that GRANTS a mask, by any phrasing
grant = {}          # mask lower -> (achievement, kind)
for a in A:
    for m in a["rewards"].get("masks") or []:
        grant.setdefault(m.strip().lower(), [a["name"], "achievement"])
    # "Equip the "X" mask" / "Equip the X mask" = free or community unlock
    for m in re.findall(r'Equip(?:ing)?\s+(?:the\s+)?["“]?([^"”\.,;]{2,50})["”]?\s+masks?\b', a["desc"], re.I):
        k = m.strip().lower()
        if k not in grant:
            grant[k] = [a["name"], "free"]
    # granting phrased without "Unlocks"
    for m in re.findall(r'["“]([^"”]{2,50})["”]\s+masks?\b(?!\s*(?:from|and you))', a["desc"]):
        k = m.strip().lower()
        if k not in grant and re.search(r'unlock|award|obtain|receive|earn|equip', a["desc"], re.I):
            grant[k] = [a["name"], "achievement"]

REQ = r'wearing\s+(?:one\s+different\s+)?(?:a\s+|an\s+|the\s+|their\s+)?["“]?([^"”\.,;]{2,60})["”]?\s*masks?\b'

rows = []
for a in A:
    for m in re.findall(REQ, a["desc"], re.I):
        k = m.strip().lower()
        src = grant.get(k)
        if not src:
            rows.append({"need": a["name"], "mask": m.strip(), "from": None, "kind": "unknown"})
        elif src[1] == "achievement":
            rows.append({"need": a["name"], "mask": m.strip(), "from": src[0], "kind": "chain"})
        else:
            rows.append({"need": a["name"], "mask": m.strip(), "from": src[0], "kind": "free"})

from collections import Counter
print("требований маски всего:", len(rows))
print(Counter(r["kind"] for r in rows))
print()
print("=== ЦЕПОЧКИ (маска из достижения) ===")
for r in rows:
    if r["kind"] == "chain":
        print(f"   маска «{r['mask']}» даётся достижением «{r['from']}» → нужно для «{r['need']}»")
print()
print("=== БЕСПЛАТНЫЕ / COMMUNITY (мешают, но не зависят от хайста) ===")
for r in rows:
    if r["kind"] == "free":
        print(f"   маска «{r['mask']}» — бесплатно/ивент («{r['from']}») → нужно для «{r['need']}»")
print()
print("=== НЕИЗВЕСТНЫЙ ИСТОЧНИК ===")
for r in rows:
    if r["kind"] == "unknown":
        print(f"   маска «{r['mask']}» → нужно для «{r['need']}»")
json.dump(rows, open("payday/data/mask_requirements.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)