# -*- coding: utf-8 -*-
"""Clean up heist attribution: drop wrong links, mark shared/variant ones.

An achievement may legitimately show up on two pages because a DLC pack reuses
another heist's map (Hardcore Henry runs the Murky Station map). That is not a
second achievement -- it must be flagged so counts never double it.
"""
import json, re, sys, io
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from heist_aliases import key_for, norm
from heuristics import HEISTS

data = json.load(open("payday/data/app_final.json", encoding="utf-8"))
A = data["achievements"]

# every heist key currently in use, with a human label
label = {}
for h in data["heists"]:
    ru = h.get("name_ru") or h["name"]
    for probe in (h["page"], h["name"], h.get("job") or ""):
        if probe:
            label.setdefault(key_for(probe), ru)

# keys that are genuinely a different heist sharing nothing
shared_map = {  # pack heist -> the base heist whose map it reuses
    "Prison Nightmare": "Hoxton Breakout",
}

fixed, dropped, marked = 0, [], []
for a in A:
    keys = list(a.get("heists") or [])
    if not keys:
        continue
    wiki = set(a.get("wiki_heists") or [])
    wiki_keys = {key_for(w) for w in wiki}

    # 1. drop keys that contradict the wiki AND have no textual support
    #    (the wiki lists a row on specific pages; a source-page dump or an
    #    alias hit may still have hung sibling keys on it -- "Nightmare
    #    Machine" carried hoxton_breakout while its text says Prison Nightmare
    #    and the wiki knows only Prison Nightmare)
    kept, dropped = [], []
    for k in keys:
        if k in wiki_keys:
            kept.append(k)
            continue
        kk = key_for(k)
        nm, aliases = HEISTS.get(kk, (kk.replace("_", " "), []))
        t = re.sub(r'"[^"]*"', " ", (a.get("desc") or "").lower())
        supported = any(re.search(r"(?<![a-z])" + re.escape(x.lower()) + r"(?![a-z])", t)
                        for x in [nm] + list(aliases))
        if supported:
            kept.append(k)
        else:
            dropped.append(k)
    if dropped:
        a["dropped_heists"] = dropped
    a["heists"] = kept

    # 2. mark achievements the wiki lists under a different heist as well
    if len(wiki_keys) > 1 or (wiki and len(kept) > len(wiki_keys)):
        a["shared_pages"] = sorted(wiki)
        marked.append(a["name"])

    # 3. separate "can also be done here" from "is this heist's achievement"
    if a.get("category") in ("collect", "count", "crew") or a.get("needs_masks"):
        a["fit"] = "extra"
    else:
        a["fit"] = "own"

# ---- integrity repairs surfaced by the verifier ---------------------------
# 1. Steam ships one achievement with an empty description ("The End"); the
#    Russian wiki has one, so borrow it rather than render an empty card.
borrowed = 0
for a in A:
    if not str(a.get("desc") or "").strip() and str(a.get("desc_ru") or "").strip():
        a["desc"] = a["desc_ru"]
        a["desc_borrowed"] = True
        borrowed += 1

# 2. An achievement can carry a heist key that never resolved to a registry
#    heist (a false alias hit). Such a row would appear on no page at all, so
#    it has to move to the global bucket where the UI can still show it.
known = set()
for h in data["heists"]:
    for probe in (h["page"], h["name"], h.get("job") or ""):
        if probe:
            known.add(key_for(probe))
            known.add(norm(probe))
    for v in (h.get("variants") or []):
        known.add(norm(v.get("ru") or ""))
        known.add(norm(v.get("en") or ""))

in_heist = set()
for h in data["heists"]:
    in_heist |= set(h["ids"])
    for v in (h.get("variants") or []):
        in_heist |= set(v["ids"])

global_ids = set(data.get("global_ids") or [])
orphan_keys, moved = set(), 0
for a in A:
    if a["id"] in in_heist or a["id"] in global_ids:
        continue
    bad = [k for k in (a.get("heists") or [])
           if key_for(k) not in known and norm(k) not in known]
    if bad:
        a["heists"] = [k for k in a["heists"] if k not in bad]
        a["dropped_heists"] = bad
        orphan_keys.update(bad)
        global_ids.add(a["id"])
        moved += 1
if moved:
    data["global_ids"] = sorted(global_ids)

json.dump(data, open("payday/data/app_final.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("описание взято из RU, где Steam пуст:", borrowed)
print("отправлено в общие из-за несуществующего хайста:", moved)
print("неизвестные ключи хайстов:", sorted(orphan_keys)[:8])
print("достижений с отметкой «можно дополнительно»:", sum(1 for a in A if a.get("fit") == "extra"))
print("достижений, числящихся на нескольких страницах вики:", len(marked))
print("разбивка по пригодности:", Counter(a.get("fit") for a in A))
print()
print("примеры «можно дополнительно»:")
for a in [x for x in A if x.get("fit") == "extra"][:10]:
    print(f"   {a['name'][:38]:40s} {a['category']:12s} heists={a['heists']}")