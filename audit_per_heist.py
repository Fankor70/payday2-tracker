# -*- coding: utf-8 -*-
"""Per-heist reconciliation, resolved so folded/variant parents compare fairly.

Three mappings have to be normalised first, otherwise every folded heist looks
empty and every variant looks like an intruder:
  * a folded parent (The Bomb Heists) collects its members' ids
  * a variant (Transport: Crossroads) belongs to its parent's key
  * the wiki writes names with typos, so matching is fuzzy within a tolerance
"""
import json, re, sys, io, difflib
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from heist_aliases import key_for, norm

data = json.load(open("payday/data/app_final.json", encoding="utf-8"))
linked = json.load(open("payday/data/ru_linked.json", encoding="utf-8"))
A = data["achievements"]
by_id = {a["id"]: a for a in A}

# --------------------------------------------------- wiki names per heist key
wiki_by_heist = defaultdict(dict)          # key -> {norm name: original name}
for key, v in linked.items():
    k = key_for(key)
    for e in v["entries"]:
        if e.get("name_en"):
            wiki_by_heist[k].setdefault(norm(e["name_en"]), e["name_en"])

# --------------------------------------------------- tracker ids per heist key
mine_by_heist = defaultdict(set)
variant_to_parent = {}
for h in data["heists"]:
    for k in (key_for(h["page"]), key_for(h["name"]), norm(h["page"]).replace(" ", "_")):
        mine_by_heist[k] |= set(h["ids"])
        for v in (h.get("variants") or []):
            mine_by_heist[k] |= set(v["ids"])
            variant_to_parent[norm(v.get("en") or v.get("ru") or "")] = k

# A folded heist's member keys must show its ids. Derive this from the data
# itself -- hand-written aliases drifted out of sync with the registry.
ALIAS_OF = {}
for _h in data["heists"]:
    _hk = key_for(_h["page"])
    for _v in (_h.get("variants") or []):
        for _label in (_v.get("en"), _v.get("ru")):
            if _label:
                ALIAS_OF[key_for(_label)] = _hk



def resolve(key):
    """Merge a wiki key into the tracker key it was folded into."""
    return ALIAS_OF.get(key, key)


print("=" * 78)
print("СВЕРКА ПО ХАЙСТАМ (после слияния складок и вариантов)")
print("=" * 78)

tolerance = 0.88
total_missing, moves = 0, []
rows = []
for key in sorted(set(wiki_by_heist) | set(mine_by_heist)):
    rk = resolve(key)
    wiki = wiki_by_heist.get(key, {})
    mine = mine_by_heist.get(rk, set())
    if not wiki and not mine:
        continue
    mine_names = {norm(by_id[i]["name"]): i for i in mine if i in by_id}

    missing = []
    for wn, orig in wiki.items():
        if wn in mine_names:
            continue
        hit = difflib.get_close_matches(wn, list(mine_names), n=1, cutoff=tolerance)
        if not hit:
            missing.append(orig)
    listed_anywhere = set().union(*wiki_by_heist.values()) if wiki_by_heist else set()
    extra = sorted(n for n in (set(mine_names) - set(wiki))
                   if n not in listed_anywhere)
    total_missing += len(missing)
    rows.append((key, len(wiki), len(mine), len(missing), len(extra)))

for key, w, m, mi, ex in sorted(rows, key=lambda r: (-r[3], r[0])):
    flag = "OK " if mi == 0 else "!! "
    print(f"{flag}{key[:32]:34s} вики {w:3d} | у нас {m:3d} | нет {mi:2d} | лишних {ex:3d}")

print()
print("хостов с расхождениями:", sum(1 for r in rows if r[3]))
print("всего отсутствует у нас:", total_missing)
print("всего лишних:", sum(r[4] for r in rows))

# -------------------------------------------- what to actually move, by name
print()
print("=" * 78)
print("КУДА ДОЛЖНЫ ПЕРЕЕХАТЬ (вики знает, у нас стоит не там)")
print("=" * 78)
moves = []
for key, v in linked.items():
    rk = resolve(key_for(key))
    for e in v["entries"]:
        if not e.get("name_en"):
            continue
        aid = next((a["id"] for a in A if norm(a["name"]) == norm(e["name_en"])), None)
        if aid is None:
            aid = next((a["id"] for a in A
                        if difflib.get_close_matches(norm(a["name"]),
                                                      [norm(e["name_en"])], n=1,
                                                      cutoff=tolerance)), None)
        if aid is None:
            print("   НЕ НАЙДЕНО ВООБЩЕ:", e["name_en"])
            continue
        cur = [h["page"] for h in data["heists"] if aid in h["ids"]]
        if not cur:
            print("   нигде не привязано:", e["name_en"], "->", rk)
            moves.append({"name": e["name_en"], "to": rk, "from": None})
        elif all(resolve(key_for(c)) != rk for c in cur):
            print(f"   {e['name_en'][:40]:42s} сейчас: {cur} -> нужно: {rk}")
            moves.append({"name": e["name_en"], "to": rk, "from": cur})
json.dump(moves, open("payday/data/heist_moves.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("всего перемещений:", len(moves))