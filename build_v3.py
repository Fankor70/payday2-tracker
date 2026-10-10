# -*- coding: utf-8 -*-
"""Final dataset: RU heists, run plans, parallel-achievement section."""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from runsolver import analyse, plan, describe_run, RANK, LABEL
from scope import annotate
from runsolver import diff_spec

data = json.load(open("payday/data/app_data.json", encoding="utf-8"))
ru_heists = json.load(open("payday/data/ru_heists.json", encoding="utf-8"))

# ---- map RU heist articles onto our heists --------------------------------
by_en = {}
for v in ru_heists.values():
    if v["name_en"]:
        by_en.setdefault(v["name_en"].strip().lower(), v)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (s or "").lower())).strip()


def variants(s):
    """Looser spellings of a heist name: drop article, possessive, suffix."""
    base = norm(s)
    out = {base}
    for pre in ("the ",):
        if base.startswith(pre):
            out.add(base[len(pre):])
    out.add(base.replace("s ", " "))          # Hoxton's -> Hoxton
    out.add(re.sub(r"\s+heist$", "", base))  # Reservoir Dogs Heist -> Reservoir Dogs
    out.add(base + " heist")
    out.add(re.sub(r"\s+", "", base))
    return {v for v in out if v}


ru_by_norm = {}
for v in ru_heists.values():
    for key in (v["name_en"], v["name_ru"]):
        for k in variants(key):
            ru_by_norm.setdefault(k, v)


def ru_for(name, job, page):
    """Longest match wins. "Diamond Heist" also produces the bare variant
    "diamond", which «Бриллиант» (The Diamond) registered first -- picking the
    first hit in set order renamed «Кража бриллиантов» into «Бриллиант»."""
    best = None
    for cand in (name, job, page, page.replace(" (Payday 2)", "")):
        for k in variants(cand):
            if k in ru_by_norm and (best is None or len(k) > len(best[0])):
                best = (k, ru_by_norm[k])
    return best[1] if best else None


# ---- per-heist run plan ---------------------------------------------------
plans = {}
for h in data["heists"]:
    ach = [data["achievements"][i] for i in h["ids"]]
    if not ach:
        plans[h["page"]] = {"runs": [], "grind": [], "max_diff": "easy"}
        continue
    items = analyse(ach)
    runs, grind = plan(items)
    maxf = max((i["floor"] for i in items), key=lambda f: RANK[f])
    plans[h["page"]] = {
        "max_diff": maxf,
        "grind": grind,
        "runs": [{
            "conds": sorted(r["conds"]),
            "label": describe_run(r, maxf),
            "ach": [items[i]["name"] for i in r["items"]],
        } for r in runs],
    }

# ---- parallel / global section --------------------------------------------
A = annotate(data["achievements"])

# store the "exact difficulty" flag so the UI can mark achievements that force
# their own run (Safe House Nightmare's baby masks, for instance)
for a in A:
    _floor, a["exact"] = diff_spec(a.get("desc") or a.get("desc_ru") or "")
    a["diff"] = _floor

# "parallel" only means achievements you can actually grind during a heist;
# safe-house chores (buy, modify, spend, equip) live in their own bucket.
parallel = {"heist": [], "anywhere": [], "lobby": []}
for a in A:
    if a["heists"]:
        continue
    sc = a.get("scope", "heist")
    parallel.setdefault(sc, []).append(a["id"])

# ---- assemble -------------------------------------------------------------
out_heists = []
for h in data["heists"]:
    r = ru_for(h["name"], h.get("job", ""), h["page"])
    p = plans[h["page"]]
    out_heists.append({
        "page": h["page"],
        "name": h["name"],
        "name_ru": (r or {}).get("name_ru"),
        "desc_ru": (r or {}).get("desc"),
        "job": h.get("job", ""),
        "contractor": h["contractor"],
        "mode": h["mode"],
        "classic": h["classic"],
        "wiki": h["wiki"],
        "ids": h["ids"],
        "plan": p,
        "min_runs": len(p["runs"]),
    })

json.dump({
    "achievements": data["achievements"],
    "heists": out_heists,
    "escapes": data["escapes"],
    "global_ids": data["global_ids"],
    "parallel": parallel,
    "category_labels": data["category_labels"],
    "category_priority": data["category_priority"],
}, open("payday/data/app_base.json", "w", encoding="utf-8"), ensure_ascii=False,
    separators=(",", ":"))

print("хайстов:", len(out_heists))
print("с русским названием:", sum(1 for h in out_heists if h["name_ru"]))
print("с русским описанием:", sum(1 for h in out_heists if h["desc_ru"]))
print()
print("минимум заходов (топ-15 по числу):")
for h in sorted(out_heists, key=lambda x: -x["min_runs"])[:15]:
    print(f"   {h['min_runs']:2d} заход(а/ов)  {h['name_ru'] or h['name'][:26]:28s} "
          f"({len(h['ids'])} достижений, макс. {h['plan']['max_diff']})")
print()
print("GO Bank:", out_heists[[h["page"] for h in out_heists].index("GO Bank")]["min_runs"], "захода")
print()
print("параллельные секции:", {k: len(v) for k, v in parallel.items()})
import os
print("\nразмер:", os.path.getsize("payday/data/app_final.json") // 1024, "KB")