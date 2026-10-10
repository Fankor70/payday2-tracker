# -*- coding: utf-8 -*-
"""Final stage: merge heist variants into the base dataset and emit app_final.json."""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from runsolver import analyse, plan, describe_run, diff_spec, RANK

app = json.load(open("payday/data/app_base.json", encoding="utf-8"))
vs = json.load(open("payday/data/variants.json", encoding="utf-8"))


def make_plan(ids):
    ach = [app["achievements"][i] for i in ids]
    if not ach:
        return {"max_diff": "easy", "grind": [], "runs": []}, 0
    its = analyse(ach)
    r, g = plan(its)
    mf = max((x["floor"] for x in its), key=lambda f: RANK[f])
    return {"max_diff": mf, "grind": g,
            "runs": [{"conds": sorted(x["conds"]), "label": describe_run(x, mf),
                      "ach": [its[k]["name"] for k in x["items"]]} for x in r]}, len(r)


# 1. merges first: same heist, split across two wiki articles
#    (no merges remain: The Diamond and Diamond Heist are two contracts,
#     see build_variants.MERGE)
for cfg in vs.get("merge", []):
    keep = next((h for h in app["heists"] if h["page"] == cfg["keep"]), None)
    if not keep:
        continue
    for page in cfg["drop"]:
        other = next((h for h in app["heists"] if h["page"] == page), None)
        if other:
            keep["ids"] = sorted(set(keep["ids"]) | set(other["ids"]))
        app["heists"] = [h for h in app["heists"] if h["page"] != page]
    keep["name_ru"] = cfg.get("name_ru") or keep.get("name_ru")

# 2. drop the heists that were folded into a multi-map parent
for parent, cfg in vs.get("folded", {}).items():
    for page in cfg["drop"]:
        app["heists"] = [h for h in app["heists"] if h["page"] != page]

by_page = {h["page"]: h for h in app["heists"]}

# 2. real parents (Bank Heist, Transport)
for parent, e in vs.get("parents", {}).items():
    tgt = by_page.get(parent)
    if not tgt:
        print("  ! нет родителя", parent)
        continue
    tgt["ids"] = e["all_ids"]
    tgt["variants"] = e["variants"]
    tgt["variant_kind"] = e["kind"]

# 3. folded multi-map entries (The Bomb, Border Crossing)
for parent, cfg in vs.get("folded", {}).items():
    keep = by_page.get(cfg.get("keep"))
    if not keep:
        print("  ! нет основы складки", cfg.get("keep"))
        continue
    keep["page"] = parent
    keep["name"] = cfg.get("name_ru") or keep["name"]
    keep["name_ru"] = cfg.get("name_ru") or keep.get("name_ru")
    keep["ids"] = cfg.get("all_ids") or keep["ids"]
    keep["variants"] = cfg["variants"]
    keep["variant_kind"] = cfg["kind"]
    by_page[parent] = keep

# 3b. multi-day heists: one contract, several days, each day owns its achievements
for page, cfg in vs.get("days", {}).items():
    tgt = by_page.get(page)
    if not tgt:
        print("  ! нет хайста для дней:", page)
        continue
    tgt["variants"] = cfg["variants"]
    tgt["variant_kind"] = "day"

# 4. DLC packs hang on the heists whose maps they reuse; they are not heists
for pack, cfg in vs.get("attached", {}).items():
    for t in cfg["targets"]:
        host = by_page.get(t["page"])
        if not host:
            continue
        packs = host.setdefault("variant_packs", [])
        if pack not in packs:
            packs.append(pack)
        host["variants"] = [v for v in (host.get("variants") or [])
                            if v["ru"] != t["ru"]] + [
            {"ru": t["ru"], "en": t["en"], "own": 0, "ids": []}]
        host["variant_kind"] = host.get("variant_kind") or cfg["kind"]

for pack, cfg in vs.get("attached", {}).items():
    for t, v in zip(cfg["targets"], cfg["variants"]):
        host = by_page.get(t["page"])
        if not host:
            continue
        entry = next((x for x in (host.get("variants") or []) if x["ru"] == t["ru"]), None)
        if entry is None:
            host.setdefault("variants", []).append(
                {"ru": t["ru"], "en": t["en"], "own": 0, "ids": v["ids"]})
        else:
            entry["ids"] = sorted(set(entry["ids"]) | set(v["ids"]))

# 4b. achievements common to every variant of a heist: they are NOT part of any
#     single variant, so they get their own block ("условия на один заход")
for h in app["heists"]:
    vs = h.get("variants") or []
    if len(vs) < 2:
        continue
    shared = set(vs[0].get("shared") or [])
    for v in vs[1:]:
        shared &= set(v.get("shared") or [])
    h["shared_ids"] = sorted(shared)
    h["any_variant_ids"] = sorted(set().union(*[set(v["ids"]) for v in vs]))

# 5. plans: parent over the union, and one per variant
covered = set()
for h in app["heists"]:
    h["plan"], h["min_runs"] = make_plan(h["ids"])
    for v in (h.get("variants") or []):
        covered |= set(v["ids"])
        covered |= set(v.get("shared") or [])
    covered |= set(h.get("shared_ids") or [])
for h in app["heists"]:
    for v in (h.get("variants") or []):
        v["plan"], v["min_runs"] = make_plan(v["ids"])

app["global_ids"] = sorted(set(app["global_ids"]) - covered)

# difficulty fallback: the Russian text arrives from the wiki lists in
# build_ru_linked, i.e. AFTER build_v2 computed the difficulty list. Some
# English strings omit the difficulty while the Russian one names it.
for a in app["achievements"]:
    if not a.get("difficulties") and a.get("desc_ru"):
        _d, _ex = diff_spec(a["desc_ru"])
        if _d != "easy":
            a["difficulties"] = [_d]
            a["exact"] = _ex
            a["diff"] = _d

# 6. safety net: an achievement can carry a heist key that never resolved to a
# registry heist (a false alias match). Nothing would ever display it, so pull it
# back into the global bucket instead of losing it silently.
in_any = set(app["global_ids"])
for h in app["heists"]:
    in_any |= set(h["ids"])
    in_any |= set(h.get("shared_ids") or [])
    for v in (h.get("variants") or []):
        in_any |= set(v["ids"])
        in_any |= set(v.get("shared") or [])
orphans = sorted(set(range(len(app["achievements"]))) - in_any)
for i in orphans:
    app["global_ids"].append(i)
app["global_ids"] = sorted(set(app["global_ids"]))
if orphans:
    print("  возвращено в общие:", len(orphans),
          [app["achievements"][i]["name"][:28] for i in orphans[:5]])

json.dump(app, open("payday/data/app_final.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("\nхайстов:", len(app["heists"]))
print("с разновидностями:", sum(1 for h in app["heists"] if h.get("variants")))
print("глобальных достижений:", len(app["global_ids"]))
print("покрыто хайстами:", sum(len(h["ids"]) for h in app["heists"]))
print()
for h in app["heists"]:
    if h.get("variants"):
        pk = h.get("variant_packs") or []
        print(f"  {(h['name_ru'] or h['name'])[:24]:26s} {len(h['ids']):3d} | " +
              " | ".join(f"{v['ru']}({len(v['ids'])})" for v in h["variants"]) +
              (f"  [{', '.join(pk)}]" if pk else ""))