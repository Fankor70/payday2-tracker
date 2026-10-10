# -*- coding: utf-8 -*-
"""Build the structured PAYDAY 2 achievement dataset from parsed wiki data."""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from heuristics import HEISTS, SOURCE_HEISTS, DIFF_ORDER

ach = json.load(open("payday/data/ach_parsed.json", encoding="utf-8"))

# alias -> key, longest alias first so "the diamond heist" wins over "diamond heist"
ALIAS = []
for k, (nm, aliases) in HEISTS.items():
    for a in aliases:
        ALIAS.append((a.lower(), k))
ALIAS.sort(key=lambda x: -len(x[0]))

STOP = {"the diamond job", "the diamond heist"}


def detect_heists(text, source):
    t = text.lower()
    hits = []
    for a, k in ALIAS:
        if re.search(r"(?<![a-z])" + re.escape(a) + r"(?![a-z])", t):
            if k not in hits:
                hits.append(k)
    src = SOURCE_HEISTS.get(source, [])
    for k in src:
        if k not in hits:
            hits.append(k)
    return hits


def detect_difficulty(text):
    t = text.lower()
    found = []
    for d in DIFF_ORDER:
        if re.search(r"(?<![a-z])" + re.escape(d) + r"(?![a-z])", t):
            found.append(d)
    return found


def extract_rewards(desc):
    """Pull reward items out of 'Unlocks "X" mask, "Y" material and "Z" pattern.'"""
    rw = {"masks": [], "patterns": [], "materials": [], "weapons": [], "suits": [],
          "outfits": [], "characters": [], "other": []}
    if not re.search(r"[Uu]nlock", desc):
        return rw
    # mask:  Unlocks "Name" mask  |  Unlocks "[[Masks (Payday 2)#Sec|The Cursed One]]" mask
    for m in re.finditer(r'Unlocks?\s+(?:the\s+)?["“]?([^"”\.,;]{2,60})["”]?\s+mask', desc, re.I):
        rw["masks"].append(m.group(1).strip())
    for m in re.finditer(r'(?:the\s+)?["“]([^"”]{2,60})["”]\s+material', desc, re.I):
        rw["materials"].append(m.group(1).strip())
    for m in re.finditer(r'(?:the\s+)?["“]([^"”]{2,60})["”]\s+pattern', desc, re.I):
        rw["patterns"].append(m.group(1).strip())
    for m in re.finditer(r'["“]([^"”]{2,60})["”]\s+(pistol|shotgun|smg|rifle|sniper|lmg|heavy|bow|melee|weapon)', desc, re.I):
        rw["weapons"].append(m.group(1).strip())
    for m in re.finditer(r'["“]([^"”]{2,60})["”]\s+(?:melee\s+)?weapon', desc, re.I):
        rw["weapons"].append(m.group(1).strip())
    for m in re.finditer(r'["“]([^"”]{2,60})["”]\s+(?:as a playable character|character)', desc, re.I):
        rw["characters"].append(m.group(1).strip())
    for k in rw:
        rw[k] = sorted(set(rw[k]))
    return rw


CATS = [
    ("difficulty_ladder", r"(?<![a-z])(easy|normal|hard|very hard|overkill|mayhem|death wish|below zero|death sentence)(?![a-z])"),
    ("four_crew",         r"four man crew|4 man crew|four-player|four player|each (?:wearing|using)|one different"),
    ("no_alarm",          r"without (?:triggering|sounding|setting off|raising)[^.,]{0,20}alarm|silent|no alarm|never (?:raise|trigger)"),
    ("no_damage",         r"without taking damage|without being (?:hit|shot)|no damage|untouched|untarnished"),
    ("speed_run",         r"under \d+ minutes? |in under \d+|within \d+ minutes?|in \d+ seconds"),
    ("kill_count",        r"\b\d+\s+(?:enemies|civilians|guards|hostages|kills|dozers|bulldozers|clones)\b"),
    ("one_bag_carry",     r"(?:only|single) (?:one )?bag|one bag carry|carrying only"),
    ("cash_only",         r"cash only|only cash|no bags? (?:of )?loot"),
    ("mask_loadout",      r"wearing|mask|loadout|outfit|unlock.*\bhelmet\b"),
    ("weapon_specific",   r"with (?:a|the|your) [^.]{0,40}(?:pistol|shotgun|smg|rifle|sniper|lmg|melee)|using [^.]{0,30}(?:only|without)"),
    ("score_threshold",   r"(?:reach|get|obtain|secure) \d+|score of \d+|\d+ (?:bags?|pieces?|bars?)"),
    ("interact_object",   r"interact|placeholder|use the |answer |type in|keypad|code"),
    ("hostage_task",      r"hostage|trade|answer the call|deploy the|carry the"),
    ("secret_object",     r"secret|hidden|optional"),
    ("infamy_reward",     r"infamy"),
    ("level_reward",      r"reach level|character level|level \d+"),
    ("free_content",      r"steam community|community group|joining the"),
    ("boss_specific",     r"dozer|bulldozer|titan|bag carrier|spoaer|clerk|shark|butcher|matilda"),
]

def classify(desc):
    t = desc.lower()
    tags = [name for name, pat in CATS if re.search(pat, t)]
    return tags

# ---- build records -------------------------------------------------------
recs = []
for a in ach:
    d = a["desc"]
    heists = detect_heists(d, a["source"])
    diffs = detect_difficulty(d)
    rw = extract_rewards(d)
    tags = classify(d)
    recs.append({
        "name": a["name"],
        "desc": d,
        "source": a["source"],
        "heists": heists,
        "difficulties": diffs,
        "max_difficulty": diffs[-1] if diffs else None,
        "rewards": {k: v for k, v in rw.items() if v},
        "tags": tags,
        "has_reward": bool(rw["masks"] or rw["patterns"] or rw["materials"] or rw["weapons"] or rw["characters"]),
    })

json.dump(recs, open("payday/data/ach_final.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- stats ---------------------------------------------------------------
print("achievements:", len(recs))
withheist = [r for r in recs if r["heists"]]
print("with detected heist:", len(withheist))
print("with difficulty:", sum(1 for r in recs if r["difficulties"]))
print("with reward:", sum(1 for r in recs if r["has_reward"]))
print("with 4-crew condition:", sum(1 for r in recs if "four_crew" in r["tags"]))
print("with no_alarm:", sum(1 for r in recs if "no_alarm" in r["tags"]))
print()
from collections import Counter
c = Counter()
for r in recs:
    for h in r["heists"]:
        c[h] += 1
print("achievements per heist:")
for k, v in c.most_common(40):
    print(f"   {v:4d}  {HEISTS.get(k,(k,))[0]}")
print()
print("heists with 0 achievements:", len(HEISTS) - len(c))
for k in HEISTS:
    if k not in c:
        print("    -", HEISTS[k][0])