# -*- coding: utf-8 -*-
"""Heist variants.

Two kinds, and they behave differently:
  loot — same map, the prize differs. Bank Heist: Cash / Deposit / Gold / Random.
         Each variant has its OWN difficulty ladder (8 achievements each), plus the
         generic ones that work on any variant.
  map  — different maps under one contract entry (Transport's five, The Bomb's two).
         DLC variant packs reuse existing maps entirely, so they are attached to
         the base heist rather than added as new ones: Hardcore Henry IS Murky
         Station + Boiling Point, Point Break IS Beneath the Mountain + Birth of
         Sky, John Wick IS Brooklyn 10-10. Counting those packs as heists is what
         pushed the list from 81 to 86 and was wrong.
"""
import json, re, sys, io
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

data = json.load(open("payday/data/app_base.json", encoding="utf-8"))
A = data["achievements"]
pages = {h["page"]: h for h in data["heists"]}


def ids_of(page_like):
    if page_like in pages:
        return list(pages[page_like]["ids"])
    key = page_like.lower().replace(" (payday 2)", "")
    for p, h in pages.items():
        if p.lower().replace(" (payday 2)", "") == key:
            return list(h["ids"])
    for p, h in pages.items():
        if key in p.lower():
            return list(h["ids"])
    return []


def split_by(ids, names):
    """Route each achievement to the first variant name it mentions."""
    buckets = {n: [] for n in names}
    shared = []
    for i in ids:
        d = (A[i]["desc"] or "") + " " + (A[i].get("desc_ru") or "")
        hit = None
        for n in names:
            pat = r"(?<![a-z])" + re.escape(n).replace("'", "[’']") + r"(?![a-z])"
            if re.search(pat, d, re.I):
                hit = n
                break
        (buckets[hit] if hit else shared).append(i)
    return buckets, shared


# ---------------------------------------------------------------- definitions
# parent page -> (kind, [(ru name, match key, base-heist page or None)])
VARIANTS = {
    "Bank Heist": ("loot", [
        ("Деньги", "Cash", None),
        ("Ячейки", "Deposit", None),
        ("Золото", "Gold", None),
        ("Случайное", "Random", None),
    ]),
    "Transport": ("map", [
        ("Парк", "Park", None), ("Центр города", "Downtown", None),
        ("Проезд", "Underpass", None), ("Перекресток", "Crossroads", None),
        ("Гавань", "Harbor", None),
    ]),

}

# multi-map entries that already exist as SEPARATE heists: fold them into one parent
FOLD = [
    {"parent": "Basics", "drop": ["Get the Coke"],
     "keep": "Flash Drive", "name_ru": "Обучение", "kind": "tutorial",
     "variants": [("Основы скрытности", "Stealth Basics", "Flash Drive"),
                  ("Основы ведения боя", "Loud Basics", "Get the Coke")]},
    {"parent": "The Bomb Heists", "drop": ["The Bomb: Dockyard"],
     "keep": "The Bomb: Forest", "name_ru": "Бомба", "kind": "map",
     "variants": [("Лес", "Forest", "The Bomb: Forest"),
                  ("Доки", "Dockyard", "The Bomb: Dockyard")]},
    {"parent": "Border Crossing Heists", "drop": ["Border Crystals"],
     "keep": "Border Crossing", "name_ru": "Пересечение границы", "kind": "map",
     "variants": [("Пересечение границы", "Border Crossing", "Border Crossing"),
                  ("Кристаллы на границе", "Border Crystals", "Border Crystals")]},
]

# DLC packs that add variants to heists that already exist: no new heist entry
ATTACH = [
    {"pack": "Hardcore Henry", "pack_ru": None, "kind": "map",
     "variants": [("Кувалда", "Rack 'Em", "Murky Station"),
                  ("Котёл", "Cauldron", "Boiling Point")]},
    {"pack": "The Point Break Heists", "pack_ru": None, "kind": "map",
     "variants": [("Лыжный курорт", "Ski Resort", "Beneath the Mountain"),
                  ("Сёрф-клуб", "Surf Club", "Birth of Sky")]},
    {"pack": "John Wick Heists", "pack_ru": None, "kind": "map",
     "variants": [("Бруклин 10-10", "Checkout", "Brooklyn 10-10"),
                  ("Яхта", "Professor", "The Yacht Heist")]},
]

# Transport's per-map achievements ("Transport: Crossroads job") never matched the
# "armored transport" alias, so they are attached to no heist. Scan the WHOLE list
# -- build_v3 strips claimed ids from global_ids, so a later run would lose them.
transport_ids = set()
for i in range(len(A)):
    d = (A[i]["desc"] or "") + " " + (A[i].get("desc_ru") or "")
    if re.search(r"(?i)\btransport\s*:\s*", d):
        transport_ids.add(i)
transport_ids |= set(pages.get("Transport", {}).get("ids", []))

# «Бриллиант» (The Diamond) и «Кража бриллиантов» (Diamond Heist) — РАЗНЫЕ
# контракты, а не один: у каждого своя лестница сложностей в текстах игры
# («Complete The Diamond job…» против «Complete the Diamond Heist on…»), и у
# вики две отдельные статьи с отдельными списками. Раньше они здесь сливались,
# и «Кража бриллиантов» показывала 28 достижений вместо своих 16.
MERGE = []


out = {"parents": {}, "attached": {}, "folded": {}, "days": {}}

# ---------------------------------------------------------------- 1. real parents
for parent, (kind, raw) in VARIANTS.items():
    base = pages.get(parent)
    if not base:
        print("  ! нет хайста", parent)
        continue
    names = [r[1] for r in raw]
    src = sorted(transport_ids) if parent == "Transport" else list(base["ids"])
    buckets, shared = split_by(src, names)

    variants = []
    for ru, key, _ in raw:
        own = buckets.get(key, [])
        # a variant shows ONLY what belongs to it -- merging the common ones into
        # every tab made each tab look like it owned achievements it does not
        variants.append({"ru": ru, "en": key, "own": len(own),
                         "ids": sorted(set(own)), "shared": sorted(shared)})

    base["ids"] = sorted(set(src))
    out["parents"][parent] = {
        "page": parent, "name": base["name"], "name_ru": base.get("name_ru"),
        "kind": kind, "variants": variants, "shared": sorted(shared),
        "all_ids": sorted(set(src)),
    }
    print(f"{parent:16s} {kind:5s} разновидностей {len(variants)}, "
          f"своих {sum(v['own'] for v in variants)}, общих {len(shared)}")

# ---------------------------------------------------------------- 2. fold pairs
for cfg in FOLD:
    keep = pages.get(cfg["keep"])
    if not keep:
        print("  ! нет хайста", cfg["keep"])
        continue
    names = [v[1] for v in cfg["variants"]]
    src = []
    for _ru, _k, p in cfg["variants"]:
        src += ids_of(p)
    buckets, shared = split_by(sorted(set(src)), names)
    variants = []
    for ru, key, p in cfg["variants"]:
        own = buckets.get(key, [])
        ids = sorted(set(own)) or sorted(set(ids_of(p)))
        variants.append({"ru": ru, "en": key, "own": len(own), "ids": ids,
                         "shared": sorted(shared)})
    keep["name"] = cfg["name_ru"] or keep["name"]
    keep["page"] = cfg["parent"]
    keep["variants"] = variants
    keep["variant_kind"] = cfg["kind"]
    keep["variant_pack"] = cfg["parent"]
    keep["ids"] = sorted(set(src))
    pages[cfg["parent"]] = keep
    out["folded"][cfg["parent"]] = {
        "drop": cfg["drop"], "keep": cfg["keep"],
        "kind": cfg["kind"], "name_ru": cfg["name_ru"],
        "all_ids": sorted(set(src)),
        "variants": variants,
    }
    print(f"{cfg['parent']:24s} складка: {[v['ru']+'('+str(len(v['ids']))+')' for v in variants]}, "
          f"убрано отдельных хайстов {len(cfg['drop'])}")

# ---------------------------------------------------------------- 3. attach packs
for cfg in ATTACH:
    variants = []
    for ru, key, base_page in cfg["variants"]:
        ids = sorted(set(ids_of(base_page)))
        variants.append({"ru": ru, "en": key, "own": len(ids), "ids": ids})
    out["attached"][cfg["pack"]] = {
        "kind": cfg["kind"],
        "targets": [{"page": v_base, "ru": ru, "en": key}
                    for ru, key, v_base in cfg["variants"]],
        "variants": variants,
    }
    print(f"{cfg['pack']:24s} → привязка к существующим хайстам: "
          f"{[t['page'] for t in out['attached'][cfg['pack']]['targets']]}")

out["merge"] = MERGE
from days import make_day_variants
out["days"] = make_day_variants(pages, A)
out["days"] = make_day_variants(pages, A)
json.dump(out, open("payday/data/variants.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nродителей:", len(out["parents"]), "| складок:", len(out["folded"]),
      "| навешено паков:", len(out["attached"]))