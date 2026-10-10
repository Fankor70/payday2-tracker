# -*- coding: utf-8 -*-
"""Audit heist attribution: which achievements really belong where.

Two different things get mixed in the current model:
  * an achievement that IS this heist's (its own ladder, its own objective)
  * an achievement that can also be done while running this heist (any-heist
    counters, 4-player crew conditions, mask-set requirements)
Both belong on the page, but they must not be counted the same way.
"""
import json, re, sys, io
from collections import defaultdict, Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")

data = json.load(open("payday/data/app_final.json", encoding="utf-8"))
linked = json.load(open("payday/data/ru_linked.json", encoding="utf-8"))
A = data["achievements"]

# ---- what the wiki lists under each heist -----------------------------------
# the wiki names heists for humans ("Bank Heist"), the heuristics use internal
# keys ("bank_heist") -- normalise both into one key space before comparing
def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (s or "").lower())).strip()


wiki_of = {}
for key, v in linked.items():
    for e in v["entries"]:
        if e.get("name_en"):
            wiki_of.setdefault(e["name_en"].strip().lower(), set()).add(key)

wiki_norm = {}
for name, hs in wiki_of.items():
    wiki_norm.setdefault(norm(name), set()).update(hs)

# ---- heist key -> registry page (for display) ------------------------------
pages = {h["page"]: h for h in data["heists"]}


def label(key):
    for h in data["heists"]:
        if key in h["ids"]:
            return h.get("name_ru") or h["name"]
    return key


print("=" * 74)
print("ПРИВЯЗКА ДОСТИЖЕНИЙ К ХАЙСТАМ")
print("=" * 74)

on_wiki, heuristic_only, not_listed = [], [], []
for a in A:
    w = wiki_norm.get(norm(a["name"]), set())
    mine = [k for k in (a.get("heists") or [])]
    if w:
        on_wiki.append((a, w))
        wn = {norm(x) for x in w}
        extra = [k for k in mine if norm(k) not in wn and norm(k.replace("_", " ")) not in wn]
        if extra:
            a["heists_extra"] = extra
    elif mine:
        heuristic_only.append((a, mine))
    else:
        not_listed.append(a)

print("достижений, перечисленных вики за хайстом:", len(on_wiki))
print("привязано только эвристикой (вики нет в списках):", len(heuristic_only))
print("без хайста вовсе:", len(not_listed))
print()

print("--- ЭВРИСТИКА ПРИСВАИЛА ЛИШНЕЕ, ЧЕМ ЕСТЬ НА ВИКИ ---")
extra_count = 0
for a, w in on_wiki:
    extra = a.get("heists_extra") or []
    if extra:
        extra_count += len(extra)
        print(f"   {a['name'][:38]:40s}")
        print(f"       вики:   {sorted(w)}")
        print(f"       лишнее: {extra}")
print("всего лишних привязок:", extra_count)
print()

print("--- ТОЛЬКО ЭВРИСТИКА (проверить глазами) ---")
for a, mine in heuristic_only[:20]:
    print(f"   {a['name'][:36]:38s} {mine} | {a['desc'][:52]}")

json.dump({"extra": [{"id": a["id"], "name": a["name"], "extra": a["heists_extra"]}
                    for a, w in on_wiki if a.get("heists_extra")]},
          open("payday/data/attribution_issues.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)