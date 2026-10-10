# -*- coding: utf-8 -*-
"""Assemble the final dataset for the tracker, including mask dependency chains."""
import json, re, sys, io
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from heuristics import HEISTS

ach = json.load(open("payday/data/ach_merged.json", encoding="utf-8"))
reg = json.load(open("payday/data/heist_registry.json", encoding="utf-8"))

# ------------------------------------------------------------------ taxonomy
CATEGORY_LABELS = {
    "difficulty_ladder": "Лестница сложности",
    "contractor_ladder": "Все контракты подряд",
    "crew": "Нужна команда из 4",
    "run_condition": "Условие на один заход",
    "count": "Счётчик (киллы / сумки)",
    "mask_loadout": "Маски и снаряжение",
    "weapon": "Конкретное оружие",
    "boss": "Боссы и спец-цели",
    "collect": "Накопительные (общие)",
    "free": "Бесплатно / за сообщество",
    "other": "Прочие",
}

PRIORITY = ["contractor_ladder", "crew", "difficulty_ladder", "run_condition",
            "count", "mask_loadout", "weapon", "boss", "collect", "free"]


def primary_category(r):
    t = set(r["tags"])
    src = r["source"]
    desc = r["desc"]
    if not r["heists"] and re.search(r"all (?:of|contracts|classic|event)", desc, re.I):
        return "contractor_ladder"
    if not r["heists"]:
        return "collect"
    if "four_crew" in t:
        return "crew"
    if "difficulty_ladder" in t and len(r["difficulties"]) == 1 and re.search(
            r"^(complete|finish|in|on)\b", desc, re.I):
        return "difficulty_ladder"
    if t & {"no_alarm", "no_damage", "speed_run", "one_bag_carry", "cash_only"}:
        return "run_condition"
    if t & {"kill_count", "score_threshold"}:
        return "count"
    if "free_content" in t:
        return "free"
    if "weapon_specific" in t or "boss_specific" in t:
        return "weapon" if "weapon_specific" in t else "boss"
    if "mask_loadout" in t:
        return "mask_loadout"
    if "difficulty_ladder" in t:
        return "difficulty_ladder"
    return "other"


# ------------------------------------------------------- mask dependency map
# The English wiki names the reward mask in only ~90 rows; the Russian wiki
# states "открывает маску «X»" far more often, so harvest it to widen the table.
RU_MASK = re.compile(r"маск\w*\s*«([^»]{2,60})»", re.I)
RU_PAT = re.compile(r"рисун\w*\s*«([^»]{2,60})»", re.I)
RU_MAT = re.compile(r"материал\w*\s*«([^»]{2,60})»", re.I)

mask_owner = {}          # mask name -> achievement name that unlocks it
mask_owner_ru = {}       # russian mask name -> achievement name
for r in ach:
    for m in (r.get("rewards") or {}).get("masks", []):
        mask_owner.setdefault(m.strip().lower(), r["name"])
    ru = r.get("desc_ru") or ""
    if ru:
        for m in RU_MASK.findall(ru):
            mask_owner_ru.setdefault(m.strip().lower(), r["name"])
            if "ru_masks" not in r:
                r["ru_masks"] = []
            if m.strip() not in r["ru_masks"]:
                r["ru_masks"].append(m.strip())
        for rx, key in ((RU_PAT, "ru_patterns"), (RU_MAT, "ru_materials")):
            vals = rx.findall(ru)
            if vals:
                r.setdefault(key, sorted(set(v.strip() for v in vals)))

# every phrasing that names the mask an achievement wants equipped
MASK_PATTERNS = [
    r'wearing\s+(?:one\s+different\s+)?(?:a\s+|an\s+|the\s+|their\s+)?["“]?([^"”\.,;]{2,60})["”]?\s*mask',
    r'wearing\s+(?:the\s+)?["“]([^"”]{2,60})["”]\s*mask',
    r'mask\s+["“]([^"”]{2,60})["”]',
    r'["“]([^"”]{2,60})["”]\s+mask\s+each',
]
# Russian equivalents: "носящие 4 разные маски «X»"
MASK_PATTERNS_RU = [
    r'носящие[^.]{0,40}?маски?\s*["«]([^"»]{2,60})["»]',
    r'["«]([^"»]{2,60})["»]\s*маски',
    r'надет[^.]{0,30}?["«]([^"»]{2,60})["»]',
]
ANY_MASK_REQ = re.compile(r"wearing|носят|носящ|надет", re.I)


def find_mask_deps(text, owner_name):
    out = []
    for pat in MASK_PATTERNS:
        for m in re.findall(pat, text, re.I):
            k = m.strip().lower()
            owner = mask_owner.get(k)
            if owner and owner != owner_name:
                out.append({"mask": m.strip(), "unlocked_by": owner})
    return out


for r in ach:
    deps = find_mask_deps(r["desc"], r["name"])
    ru_desc = r.get("desc_ru") or ""
    # RU rows name the required masks in guillemets, e.g. «маску „Деннис“»
    if ru_desc:
        for m in RU_MASK.findall(ru_desc):
            owner = mask_owner_ru.get(m.strip().lower())
            if owner and owner != r["name"]:
                deps.append({"mask": m.strip(), "unlocked_by": owner, "lang": "ru"})
    seen, uniq = set(), []
    for d in deps:
        if d["mask"].lower() not in seen:
            seen.add(d["mask"].lower())
            uniq.append(d)
    r["deps"] = uniq
    r["needs_masks"] = bool(ANY_MASK_REQ.search(r["desc"] + " " + ru_desc))
    r["category"] = primary_category(r)

# ------------------------------------------------------------------ heists
KNOWN_CONTRACTOR = {
    "Flash Drive": "Bain", "Get the Coke": "Bain",
    "Counterfeit (Payday 2)": "The Elephant", "Diamond Heist (Payday 2)": "Bain",
    "First World Bank (Payday 2)": "Bain", "Green Bridge (Payday 2)": "Bain",
    "Heat Street (Payday 2)": "Bain", "No Mercy (Payday 2)": "Bain",
    "Panic Room (Payday 2)": "Bain", "Slaughterhouse (Payday 2)": "The Elephant",
    "Undercover (Payday 2)": "Bain", "Crude Awakening": "The Butcher",
    "Dragon Heist": "Jiu Feng", "Hostile Takeover": "The Butcher",
    "Lost In Transit": "The Butcher", "Midland Ranch": "Vlad",
    "Mountain Master": "Vlad", "Cursed Kill Room": "Vlad", "Goat Simulator": "Vlad",
    "Lab Rats": "The Dentist", "Prison Nightmare": "The Dentist",
    "Safe House Nightmare": "The Dentist", "Safe House Raid": "The Dentist",
}

by_heist = defaultdict(list)
for i, r in enumerate(ach):
    r["id"] = i
    for h in r["heists"]:
        by_heist[h].append(i)

# map canonical heist key -> registry page name
KEY2PAGE = {
    "the_diamond": "The Diamond", "diamond_heist": "Diamond Heist (Payday 2)",
    "slaughterhouse": "Slaughterhouse (Payday 2)",
    "counterfeit": "Counterfeit (Payday 2)",
    "first_world_bank": "First World Bank (Payday 2)",
    "green_bridge": "Green Bridge (Payday 2)",
    "heat_street": "Heat Street (Payday 2)",
    "no_mercy": "No Mercy (Payday 2)",
    "panic_room_dw": "Panic Room (Payday 2)",
    "undercover": "Undercover (Payday 2)",
    "santa_workshop": "Santa's Workshop",
}

heists = []
for h in reg["heists"]:
    page = h["page"]
    contractor = KNOWN_CONTRACTOR.get(page, h["contractor"])
    job = h.get("job", "")
    probe = (page + " " + job).lower()
    ids = set()
    matched_keys = []
    for key, (nm, aliases) in HEISTS.items():
        if KEY2PAGE.get(key) == page:
            matched_keys.append(key)
            continue
        # only the registry page/job text is probed -- never the canonical name,
        # or every heist would match its own alias and swallow all achievements
        hit = False
        for probe_str in (nm, key.replace("_", " ")):
            if probe_str and re.search(r"(?<![a-z])" + re.escape(probe_str.lower()) + r"(?![a-z])", probe):
                hit = True
                break
        if not hit:
            for a in aliases:
                if re.search(r"(?<![a-z])" + re.escape(a) + r"(?![a-z])", probe):
                    hit = True
                    break
        if hit:
            matched_keys.append(key)
    for key in matched_keys:
        ids.update(by_heist.get(key, []))
    heists.append({
        "page": page,
        "name": h["name"],
        "job": job,
        "contractor": contractor,
        "mode": h["mode"],
        "classic": h["classic"],
        "wiki": h["wiki"],
        "keys": matched_keys,
        "ids": sorted(ids),
    })

global_ids = [r["id"] for r in ach if not r["heists"]]

# ------------------------------------------------------------------ output
app = {
    "achievements": [{
        "id": r["id"],
        "name": r["name"],
        "name_ru": r.get("name_ru"),
        "desc": r["desc"],
        "desc_ru": r.get("desc_ru"),
        "heists": r["heists"],
        "difficulties": r["difficulties"],
        "max_diff": r["max_difficulty"],
        "rewards": r.get("rewards") or {},
        "tags": r["tags"],
        "category": r["category"],
        "source": r["source"],
        "deps": r["deps"],
    } for r in ach],
    "heists": heists,
    "escapes": reg["escapes"],
    "global_ids": global_ids,
    "category_labels": CATEGORY_LABELS,
    "category_priority": PRIORITY,
}
json.dump(app, open("payday/data/app_data.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("achievements:", len(ach))
print("heists:", len(heists), "| escapes:", len(reg["escapes"]))
print("global (не привязано к хайсту):", len(global_ids))
print("с зависимостью от маски:", sum(1 for r in ach if r["deps"]))
print()
print("категории:")
for k, v in Counter(r["category"] for r in ach).most_common():
    print(f"   {v:5d}  {CATEGORY_LABELS.get(k,k)}")
print()
print("топ хайстов по числу достижений:")
for h in sorted(heists, key=lambda x: -len(x["ids"]))[:12]:
    print(f"   {len(h['ids']):4d}  {h['name'][:34]:36s} {h['contractor']}")
print()
print("хайсты без достижений:", [h["name"] for h in heists if not h["ids"]])
print()
print("примеры цепочек зависимостей:")
n = 0
for r in ach:
    if r["deps"]:
        d = r["deps"][0]
        print(f"   «{d['mask']}» (даёт: {d['unlocked_by']}) нужно для: {r['name']}")
        n += 1
        if n >= 10:
            break