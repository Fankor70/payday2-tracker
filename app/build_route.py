# -*- coding: utf-8 -*-
"""Attach the route to each heist: which run closes what, and what it advances.

The minimum-runs planner only ever saw the heist's own achievements. The point
of the whole tool is that a run also moves account-wide counters, so each run now
reports:
  * its own achievements, split by planning category
  * how many farmable counters any run pushes forward
  * whether it needs a full lobby
"""
import json, sys, io, os
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PAY = os.path.dirname(HERE)
sys.path.insert(0, PAY)
from runsolver import analyse, plan, describe_run, RANK

TARGET = (sys.argv[1] if len(sys.argv) > 1
          else os.path.join(PAY, "data", "app_final.json"))
data = json.load(open(TARGET, encoding="utf-8"))
A = data["achievements"]

CAT_RU = {
    "ladder": "Лестница сложности", "run_cond": "Условия захода",
    "objective": "Объекты миссии", "loadout": "Маски и снаряжение",
    "crew": "Нужен полный состав", "farmable": "Общие счётчики",
    "meta": "Прогресс аккаунта",
}

# ------------------------------------------------------- account-wide buckets
farmable = [a for a in A if a.get("plan_cat") == "farmable"]
meta = [a for a in A if a.get("plan_cat") == "meta"]
# "Complete all contracts on <difficulty>" rows are a difficulty ladder, not a
# general grind -- they belong in their own block, not under "общие"
LADDER = ("difficulty_ladder", "contractor_ladder")
ladders = [a for a in A
           if a.get("category") in LADDER and not a.get("heists")]
heist_side = [a for a in A if a.get("heists")]

# farmable achievements that are tied to a specific heist still belong to it;
# only the genuinely global ones ride along with every run
global_farm = [a for a in farmable if not a.get("heists")]


def route_for(ids, label=""):
    ach = [A[i] for i in ids]
    if not ach:
        return {"runs": [], "min_runs": 0, "max_diff": "easy", "grind": []}
    by_name = {a["name"]: a["id"] for a in ach}
    cat_of = {a["name"]: (a.get("plan_cat") or "ladder") for a in ach}
    items = analyse(ach)
    runs, grind = plan(items)
    mf = max((x["floor"] for x in items), key=lambda f: RANK[f])
    out = []
    for r in runs:
        names = [items[k]["name"] for k in r["items"]]
        ids_in = [items[k] for k in r["items"]]
        by = Counter(cat_of.get(n, "ladder") for n in names)
        out.append({
            "label": describe_run(r, mf),
            "diff": r.get("diff"),
            "conds": sorted(r.get("conds") or []),
            "ach": names,
            "ids": [by_name.get(n) for n in names if by_name.get(n) is not None],
            "by_cat": {k: v for k, v in by.items() if v},
        })
    return {"runs": out, "min_runs": len(out), "max_diff": mf,
            "grind": grind, "cat_ru": CAT_RU}


touched = 0
for h in data["heists"]:
    ids = set(h["ids"])
    for v in (h.get("variants") or []):
        ids |= set(v["ids"])
    h["plan"] = route_for(sorted(ids))
    h["min_runs"] = h["plan"]["min_runs"]
    for v in (h.get("variants") or []):
        v["plan"] = route_for(v["ids"])
        v["min_runs"] = v["plan"]["min_runs"]
    touched += 1

data["route_meta"] = {
    "categories": [{"key": k, "ru": v} for k, v in CAT_RU.items()],
    "global_farmable": [a["id"] for a in global_farm],
    "global_meta": [a["id"] for a in meta],
    "ladders": [a["id"] for a in ladders],
    "counts": Counter(a.get("plan_cat") for a in A),
}

# the ladders leave the "общие и накопительные" bucket entirely
ladder_ids = {a["id"] for a in ladders}
data["global_ids"] = [i for i in data["global_ids"] if i not in ladder_ids]

json.dump(data, open(TARGET, "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"))

print("хайстов с маршрутом:", touched)
print("общих счётчиков (капают в любом заходе):", len(global_farm))
print("прогресс аккаунта:", len(meta))
print("лестниц контракторов (отдельный блок):", len(ladders))
print()
print("пример маршрута — GO Bank:")
gb = next((h for h in data["heists"] if h["page"] == "GO Bank"), None)
if gb:
    for i, r in enumerate(gb["plan"]["runs"], 1):
        cats = ", ".join("%s×%d" % (CAT_RU.get(k, k), v)
                        for k, v in sorted(r["by_cat"].items()))
        print(f"  Заход {i}: {r['label']}")
        print(f"      {cats}   (+{len(global_farm)} общих счётчиков попутно)")
    print(f"  Итого минимум: {gb['min_runs']} захода")