# -*- coding: utf-8 -*-
"""Rebuild the dataset on top of the authoritative Steam list (1342).

Steam gives the game's own strings plus the community unlock percentage. The
wiki is kept only for what Steam lacks: Russian text and heist attribution.
"""
import json, re, sys, io, difflib
from collections import defaultdict, Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from heuristics import HEISTS, SOURCE_HEISTS

steam = json.load(open("payday/data/steam_parsed.json", encoding="utf-8"))
merged = json.load(open("payday/data/ach_merged.json", encoding="utf-8"))
reg = json.load(open("payday/data/heist_registry.json", encoding="utf-8"))


def norm(s):
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---- index the wiki by English name -> page + russian text -----------------
wiki_by_en = {}
for r in merged:
    wiki_by_en.setdefault(norm(r["name"]), r)

all_names = sorted(wiki_by_en.keys(), key=len, reverse=True)


def wiki_lookup(name):
    k = norm(name)
    if k in wiki_by_en:
        return wiki_by_en[k]
    m = difflib.get_close_matches(k, all_names, n=1, cutoff=0.87)
    return wiki_by_en[m[0]] if m else None


# ---- heuristics ----------------------------------------------------------
DIFFS = ["easy", "normal", "hard", "very hard", "overkill", "mayhem",
         "death wish", "below zero", "death sentence"]
DIFF_ORDER = list(DIFFS)

# Reward phrasings seen in the game's own achievement strings.
# Names can contain dots ("Mrs. Claus"), apostrophes and dashes, so the name
# group must not exclude "." -- that used to silently drop those rewards.
Q = r'["“]([^"”]{2,70})["”]'
REWARD_PATTERNS = {
    # Unlocks the "X" mask   /   the "X" mask, "Y" material and "Z" pattern
    "masks": r'(?:unlocks?|unlocking)\s+(?:the\s+)?' + Q + r'\s+masks?\b',
    "outfits": r'(?:unlocks?|unlocking)\s+(?:the\s+)?' + Q + r'\s+outfits?\b',
    "materials": r'(?:unlocks?|unlocking)\s+(?:the\s+)?' + Q + r'\s+materials?\b',
    "patterns": r'(?:unlocks?|unlocking)\s+(?:the\s+)?' + Q + r'\s+patterns?\b',
    "characters": r'(?:unlocks?|unlocking)\s+' + Q + r'\s+as a playable character',
    # "... Unlocks the "Retro Foregrip" for the Falcon rifle, the "Short Barrel"
    #  for the M1014 shotgun and the "Angled sight" for all sniper rifles."
    "weapons": r'(?:unlocks?|unlocking)\s+(?:the\s+)?' + Q +
               r'\s+for\s+(?:the\s+|all\s+)?[^;]{0,70}?'
               r'\b(?:pistol|shotgun|smg|submachine|rifle|sniper|lmg|heavy|bow|melee|weapon|firearm)',
    # shorter tail forms: "Unlocks the "Solid Stock" for the M1014 shotgun."
    "weapons2": r'(?:unlocks?|unlocking)\s+(?:the\s+)?' + Q +
                r'\s+for\s+(?:the\s+|all\s+)?\w+',
    # Weapon Charm / other cosmetic unlocks that mention no weapon type
    "cosmetics": r'(?:unlocks?|unlocking)\s+(?:the\s+)?' + Q +
                 r'\s+(?:weapon charm|charm|skin|variant)\b',
    # multi-item mod lists: 'Unlocks the "A Rail", "B Rail" and "C Barrel" for the
    # CAR weapon family.' -- one quote per mod, none directly followed by "for"
    "weapons_parts": r'(?:unlocks?|unlocking)\s+(?:the\s+)?([^.;]{0,320}?)\s+for\s+'
                     r'(?:the\s+|all\s+)?[^.;]{0,70}?'
                     r'\b(?:weapon|pistol|shotgun|smg|submachine|rifle|sniper|lmg)',
    # the part noun sits right after the name: 'Unlocks the "Tank Buster" Barrel',
    # 'Unlocks the "Viper Grenade" throwable', 'Unlocks the "Stateside Conversion Kit"'
    "weapons3": r'(?:unlocks?|unlocking)\s+(?:the\s+)?' + Q +
                r'\s+(?:barrel|foregrip|front grip|stock|sight|red dot|magazine|'
                r'muzzle|receiver|upper receiver|lower receiver|grip|chamber|'
                r'suppressor|silencer|conversion kit|throwable|grenade|launcher|'
                r'charm|shield|scope|compensator|mount)\b',
}
# list form: 'Unlocks "A" mask, "B" material and "C" pattern.'
LIST_MASKS = r'["“]([^"”]{2,70})["”]\s+masks?\b'
LIST_OUTFITS = r'["“]([^"”]{2,70})["”]\s+outfits?\b'
LIST_MATERIALS = r'["“]([^"”]{2,70})["”]\s+materials?\b'
LIST_PATTERNS = r'["“]([^"”]{2,70})["”]\s+patterns?\b'
LIST_WEAPONS = r'["“]([^"”]{2,70})["”]\s+(?:melee\s+)?(?:pistol|shotgun|smg|submachine gun|rifle|sniper rifle|lmg|heavy|weapon|firearm)s?\b'


def extract_rewards(desc):
    rw = {}
    for k in ("masks", "outfits", "materials", "patterns", "characters", "cosmetics", "weapons3"):
        vals = sorted({m.strip() for m in re.findall(REWARD_PATTERNS[k], desc, re.I)})
        if not vals:
            continue
        key = "weapons" if k == "weapons3" else k
        rw[key] = sorted(set(rw.get(key, [])) | set(vals))
    # weapon mods: keep only the ones that look like a real reward list
    mods = {m.strip() for m in re.findall(REWARD_PATTERNS["weapons"], desc, re.I)}
    if len(mods) >= 2 or re.search(r"\b(?:rifle|shotgun|pistol|smg|sniper)\b", desc, re.I) and mods:
        mods |= {m.strip() for m in re.findall(REWARD_PATTERNS["weapons2"], desc, re.I)}
    for tail in re.findall(REWARD_PATTERNS["weapons_parts"], desc, re.I):
        parts = re.findall(r'["“]([^"”]{2,70})["”]', tail)
        if parts:
            mods |= {x.strip() for x in parts}
    if mods:
        rw["weapons"] = sorted(mods)
    # comma/list form, used by the DLC rows
    for key, pat in (("masks", LIST_MASKS), ("outfits", LIST_OUTFITS),
                     ("materials", LIST_MATERIALS), ("patterns", LIST_PATTERNS),
                     ("weapons", LIST_WEAPONS)):
        vals = {m.strip() for m in re.findall(pat, desc, re.I)}
        if vals:
            rw[key] = sorted(set(rw.get(key, [])) | vals)
    # catch-all: an "Unlocks the \"X\"" we could not type must still be shown
    # rather than silently dropped
    if not rw:
        left = {m.strip() for m in re.findall(
            r'(?:unlocks?|unlocking)\s+(?:the\s+)?["“]([^"”]{2,70})["”]', desc, re.I)}
        if left:
            rw["other"] = sorted(left)
    return {k: v for k, v in rw.items() if v}


CATS = [
    ("difficulty_ladder", r"(?<![a-z])(easy|normal|hard|very hard|overkill|mayhem|death wish|below zero|death sentence)(?![a-z])"),
    ("four_crew", r"four man crew|4 man crew|four-player|four player|in fours|one different mask|mask each"),
    ("no_alarm", r"without (?:triggering|sounding|setting off|raising)[^.,]{0,20}alarm|silent|no alarm"),
    ("no_damage", r"without taking damage|without being (?:hit|shot)|no damage|untouched"),
    ("speed_run", r"in under \d+ minutes?|within \d+ minutes?|in under \d+ seconds|in \d+ seconds or less"),
    ("kill_count", r"\bkill\b|\bkills\b|\bdefeat\b|\beliminate\b|\bdestroy\b"),
    ("loot_count", r"\b\d+ ?bags?\b|secure \d+|amount of loot"),
    ("mask_loadout", r"wearing|mask|loadout|outfit"),
    ("weapon_specific", r"\b(?:pistol|shotgun|smg|rifle|sniper|lmg|heavy|bow|melee|grenade)\b"),
    ("hostage_task", r"hostage|trade"),
    ("collect", r"own \d+|reach (?:reputation )?level|reach infamy|collect"),
    ("free_content", r"steam community|community group|joining the"),
]




def strip_quoted(t):
    """A quoted "Diamond Heist" names the MASK, not the contract -- game texts
    always name contracts unquoted ("the Diamond Heist on the Normal..."), so
    quoted spans must not match heist keys."""
    return re.sub(r'"[^"]*"', " ", t or "")

def heists_from_text(text):
    """Heist keys named in the achievement's own condition text.

    A condition naming "the Lab Rats job" also contains the word "rats", and
    "Transport: Train Heist" contains "transport" -- so a naive match put the
    achievement on BOTH heists and the sibling pages ended up with identical
    pools. When one matched heist's name sits inside another's, the longer name
    is what the text actually means and the shorter one is dropped.
    """
    t = strip_quoted(text.lower())
    spans = {}
    for key, (nm, aliases) in HEISTS.items():
        for a in aliases:
            for m in re.finditer(r"(?<![a-z])" + re.escape(a) + r"(?![a-z])", t):
                spans.setdefault(key, []).append((m.start(), m.end()))
    hits = list(spans)
    if len(hits) > 1:
        # "…on the San Martín Bank heist" also contains "bank heist": the
        # sub-match is the tail of a longer heist name followed by the word
        # heist, so the longer name is the contract and the sub-match goes.
        drop = set()
        for a in hits:
            for b in hits:
                if a == b:
                    continue
                for (s1, e1) in spans[a]:
                    tail = t[e1:e1 + 6]
                    if tail != " heist":
                        continue
                    for (s2, e2) in spans[b]:
                        if s2 >= s1 and e2 - 6 <= e1:
                            drop.add(b)
        hits = [k for k in hits if k not in drop]
    if len(hits) > 1:
        names = {k: HEISTS[k][0].lower() for k in hits}
        drop = {k for k in hits
                for o in hits if k != o and names[k] != names[o]
                and names[k] in names[o]}
        hits = [k for k in hits if k not in drop]
    return hits


def detect_diffs(text):
    """Difficulties named in the text, easiest first."""
    t = text.lower()
    return [d for d in DIFF_ORDER
            if re.search(r"(?<![a-z])" + re.escape(d) + r"(?![a-z])", t)]


RE_ALL_CONTRACTS = re.compile(
    r"all (?:of |the )?(?:bain|locke|vlad|hector|jimmy|the butcher|the elephant|the continental|the dentist|charon|jiu ?feng)?\s*"
    r"(?:classic|event)?\s*contracts", re.I)
RE_JOB = re.compile(r"\b(?:in|on|at|complete|finish)\s+(?:the\s+)?([A-Z][A-Za-z0-9'’:\- ]{2,40}?)\s+(?:job|heist)\b")


def category(desc, diffs, heists):
    t = desc.lower()
    tags = [n for n, p in CATS if re.search(p, t)]
    if RE_ALL_CONTRACTS.search(desc):
        return "contractor_ladder", tags
    if not heists:
        return "collect", tags
    if "four_crew" in tags:
        return "crew", tags
    if diffs and re.match(r"\s*(complete|finish|in|on)\b", desc, re.I) and "difficulty_ladder" in tags:
        return "difficulty_ladder", tags
    if tags and set(tags) & {"no_alarm", "no_damage", "speed_run", "loot_count"}:
        return "run_condition", tags
    if "kill_count" in tags:
        return "count", tags
    if "free_content" in tags:
        return "free", tags
    if "weapon_specific" in tags:
        return "weapon", tags
    if "mask_loadout" in tags:
        return "mask_loadout", tags
    if "difficulty_ladder" in tags:
        return "difficulty_ladder", tags
    return "other", tags


# ---- build ----------------------------------------------------------------
recs = []
for s in steam:
    w = wiki_lookup(s["name"])
    desc = s["desc"].strip()
    desc = re.sub(r"\s+", " ", desc)
    heists = heists_from_text(desc)
    # page-level attribution from the wiki (Steam strings often omit the heist)
    if w:
        for k in SOURCE_HEISTS.get(w["source"], []):
            if k not in heists:
                heists.append(k)
    diffs = detect_diffs(desc)
    if not diffs and w and w.get("desc_ru"):
        # the English string can omit the difficulty while the Russian one
        # names it ("The only one that is true" -> «Нормально»)
        diffs = detect_diffs(w["desc_ru"])
    rw = extract_rewards(desc)
    cat, tags = category(desc, diffs, heists)
    pct = float(s["pct"].replace("%", "")) if s["pct"] else None
    recs.append({
        "name": s["name"],
        "desc": desc,
        "pct": pct,
        "name_ru": (w or {}).get("name_ru"),
        "desc_ru": (w or {}).get("desc_ru"),
        "heists": heists,
        "difficulties": diffs,
        "rewards": rw,
        "tags": tags,
        "category": cat,
        "wiki_source": (w or {}).get("source"),
        "has_ru": bool(w and w.get("name_ru")),
    })

# ---- mask dependency chains ----------------------------------------------
mask_owner = {}
for r in recs:
    for m in r["rewards"].get("masks", []):
        mask_owner.setdefault(m.strip().lower(), r["name"])

# masks granted "for free" by an achievement that only says "Equip the X mask"
free_masks = {}
for r in recs:
    for m in re.findall(r'Equip(?:ing)?\s+(?:the\s+)?["“]?([^"”\.,;]{2,50})["”]?\s+masks?\b',
                        r["desc"], re.I):
        free_masks.setdefault(m.strip().lower(), r["name"])

# A requirement like "one different 'Diamond Heist' mask each" names a whole DLC
# mask set, not a single mask. Map those set names to the wiki subpage whose
# achievements actually hand them out.
DLC_MASK_SETS = {
    "diamond heist": "The Diamond Heist", "the diamond": "The Diamond Heist",
    "hotline miami": "Hotline Miami", "big bank": "Big Bank", "the big bank": "Big Bank",
    "assault pack": "Gage Assault Pack", "shotgun pack": "Gage Shotgun Pack",
    "sniper pack": "Gage Sniper Pack", "weapon pack": "Gage Weapon Pack 01",
    "chivalry pack": "Gage Chivalry Pack", "ninja pack": "Gage Ninja Pack",
    "brooklyn bank": "Brooklyn Bank", "brooklyn bank animal": "Brooklyn Bank",
    "diamond heist dlc": "The Diamond Heist", "go bank": "GO Bank",
    "biker": "The Biker Heist", "scarface": "Scarface Mansion",
    "prison nightmare": "Prison Nightmare", "election day": "Election Day",
    "shadow raid": "Shadow Raid", "panic room": "Panic Room",
    "meltdown": "Meltdown", "alesso": "The Alesso Heist",
    "golden grin": "Golden Grin Casino", "goat simulator": "Goat Simulator",
    "wolf pack": "Wolf Pack", "point break": "The Point Break Heists",
    "hardcore henry": "Hardcore Henry", "john wick": "John Wick Heists",
    "overwatch": "Deathwish",
}
# which achievements in each wiki subpage hand out masks
granted_by_page = {}
for r in recs:
    page = r.get("wiki_source")
    if page and r["rewards"].get("masks"):
        granted_by_page.setdefault(page, []).append(r["name"])

REQ_PATTERNS = [
    r'wearing\s+(?:one\s+different\s+)?(?:a\s+|an\s+|the\s+|their\s+)?["“]?([^"”\.,;]{2,60})["”]?\s*masks?\b',
    r'masks?\s*["“]([^"”]{2,60})["»]',
    r'["“]([^"”]{2,60})["»]\s*masks?\s+each',
]
JUNK_MASK_WORDS = {"mask", "masks", "difficulty", "any", "the", "a", "different", "one"}

for r in recs:
    deps = []
    for pat in REQ_PATTERNS:
        for m in re.findall(pat, r["desc"], re.I):
            m = m.strip().rstrip(",;")
            k = m.strip().lower()
            if k in JUNK_MASK_WORDS or k.endswith(" mask") or len(k) < 2:
                continue
            if k in mask_owner and mask_owner[k] != r["name"]:
                deps.append({"mask": m.strip(), "unlocked_by": mask_owner[k], "kind": "chain"})
            elif k in free_masks:
                deps.append({"mask": m.strip(), "unlocked_by": free_masks[k], "kind": "free"})
            elif k in DLC_MASK_SETS:
                page = DLC_MASK_SETS[k]
                srcs = granted_by_page.get(page, [])
                deps.append({
                    "mask": m.strip(),
                    "mask_set": True,
                    "unlocked_by": srcs[:6],
                    "from_dlc": page,
                    "kind": "dlc_set",
                })
            else:
                deps.append({"mask": m.strip(), "unlocked_by": None, "kind": "unknown"})
    seen, uniq = set(), []
    for d in deps:
        sig = d["mask"].lower()
        if sig not in seen:
            seen.add(sig)
            uniq.append(d)
    r["deps"] = uniq

# ---- heist index ----------------------------------------------------------
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
KEY2PAGE = {
    "the_diamond": "The Diamond", "diamond_heist": "Diamond Heist (Payday 2)",
    "slaughterhouse": "Slaughterhouse (Payday 2)", "counterfeit": "Counterfeit (Payday 2)",
    "first_world_bank": "First World Bank (Payday 2)", "green_bridge": "Green Bridge (Payday 2)",
    "heat_street": "Heat Street (Payday 2)", "no_mercy": "No Mercy (Payday 2)",
    "panic_room_dw": "Panic Room (Payday 2)", "undercover": "Undercover (Payday 2)",
    "santa_workshop": "Santa's Workshop",
    "san_martin": "San Martín Bank",
}
by_heist = defaultdict(list)
for i, r in enumerate(recs):
    r["id"] = i
    for h in r["heists"]:
        by_heist[h].append(i)

heists = []
for h in reg["heists"]:
    page, job = h["page"], h.get("job", "")
    probe = (page + " " + job).lower()
    keys = []
    for key, (nm, aliases) in HEISTS.items():
        if KEY2PAGE.get(key) == page:
            keys.append(key)
            continue
        hit = any(re.search(r"(?<![a-z])" + re.escape(s.lower()) + r"(?![a-z])", probe)
                  for s in [nm, key.replace("_", " ")] + list(aliases))
        if hit:
            keys.append(key)
    # Название страницы может содержать название соседа целиком: «Lab Rats»
    # содержит «Rats», «Transport: Train Heist» содержит «Transport». Без этой
    # правки страница наследовала весь пул соседа, и у пары хайстов наборы
    # достижений совпадали на 100%. Оставляем только самое конкретное совпадение.
    if len(keys) > 1:
        names = {k: n for k in keys
                 for n in {HEISTS[k][0].lower(), k.replace("_", " ")}}
        drop = {k for k in keys
                for o in keys if k != o
                for nk in {HEISTS[k][0].lower(), k.replace("_", " ")}
                for no in {HEISTS[o][0].lower(), o.replace("_", " ")}
                if nk != no and nk in no}
        if drop:
            keys = [k for k in keys if k not in drop]
    ids = sorted({i for k in keys for i in by_heist.get(k, [])})
    heists.append({
        "page": page, "name": h["name"], "job": job,
        "contractor": KNOWN_CONTRACTOR.get(page, h["contractor"]),
        "mode": h["mode"], "classic": h["classic"], "wiki": h["wiki"],
        "ids": ids,
    })

global_ids = [r["id"] for r in recs if not r["heists"]]

CATEGORY_LABELS = {
    "difficulty_ladder": "Лестница сложности",
    "contractor_ladder": "Все контракты подряд",
    "crew": "Нужна команда из 4",
    "run_condition": "Условие на один заход",
    "count": "Счётчик (киллы)",
    "loot": "Счётчик (лут)",
    "mask_loadout": "Маски и снаряжение",
    "weapon": "Конкретное оружие",
    "collect": "Накопительные (общие)",
    "free": "Бесплатно / за сообщество",
    "other": "Прочие",
}

app = {
    "achievements": [{
        "id": r["id"], "name": r["name"], "name_ru": r["name_ru"],
        "desc": r["desc"], "desc_ru": r["desc_ru"], "pct": r["pct"],
        "heists": r["heists"], "difficulties": r["difficulties"],
        "rewards": r["rewards"], "tags": r["tags"], "category": r["category"],
        "deps": r["deps"], "has_ru": r["has_ru"],
    } for r in recs],
    "heists": heists,
    "escapes": reg["escapes"],
    "global_ids": global_ids,
    "category_labels": CATEGORY_LABELS,
    "category_priority": ["contractor_ladder", "crew", "difficulty_ladder", "run_condition",
                          "count", "loot", "mask_loadout", "weapon", "collect", "free", "other"],
}
json.dump(app, open("payday/data/app_data.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("достижений (Steam, источник истины):", len(recs))
print("с русским переводом:", sum(1 for r in recs if r["has_ru"]))
print("привязано к хайсту:", len(recs) - len(global_ids), "| общих:", len(global_ids))
print("с наградой:", sum(1 for r in recs if r["rewards"]))
print("с процентом прохождения:", sum(1 for r in recs if r["pct"] is not None))
print("с цепочкой зависимости:", sum(1 for r in recs if r["deps"]))
print()
print("категории:")
for k, v in Counter(r["category"] for r in recs).most_common():
    print(f"   {v:5d}  {CATEGORY_LABELS.get(k, k)}")
print()
print("топ хайстов:")
for h in sorted(heists, key=lambda x: -len(x["ids"]))[:10]:
    print(f"   {len(h['ids']):4d}  {h['name'][:32]:34s} {h['contractor']}")
print("хайстов без достижений:", [h["name"] for h in heists if not h["ids"]])
print()
print("ЗАВИСИМОСТИ ПО МАСКАМ:")
for kind, label in (("chain", "маска из достижения"),
                    ("dlc_set", "набор масок из DLC"),
                    ("free", "бесплатная/community маска"),
                    ("unknown", "источник вне списка достижений")):
    items = [(r["name"], d) for r in recs for d in r["deps"] if d["kind"] == kind]
    print(f"  {label}: {len(items)}")
    for n, d in items:
        src = d.get("unlocked_by")
        src = ", ".join(src) if isinstance(src, list) else (src or "?")
        print(f"     «{d['mask']}» → нужно для «{n}» | источник: {src}")