# -*- coding: utf-8 -*-
"""Build the heist registry from wiki categories + contractor categories."""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from wikitools import find_templates

pages = json.load(open("payday/data/heist_pages.json", encoding="utf-8"))
union = json.load(open("payday/data/heist_union.json", encoding="utf-8"))
contractors = json.load(open("payday/data/contractor_heists.json", encoding="utf-8"))

C2NAME = {
    "Heists contracted by Bain": "Bain",
    "Heists contracted by The Dentist": "The Dentist",
    "Heists contracted by The Elephant": "The Elephant",
    "Heists contracted by The Butcher": "The Butcher",
    "Heists contracted by The Continental": "The Continental",
    "Heists contracted by Vlad": "Vlad",
    "Heists contracted by Locke": "Locke",
    "Heists contracted by Hector": "Hector",
    "Heists contracted by Jimmy": "Slaughterhouse",
}
MODE_CATS = {"Stealth Heists": "stealth", "Loud-Only Heists": "loud"}
ESCAPES = {"Cafe Escape", "Garage Escape", "Overpass Escape", "Park Escape", "Street Escape"}

contractor_of = {}
for cat, lst in contractors.items():
    if cat in C2NAME:
        for t in lst:
            contractor_of[t] = C2NAME[cat]

# Jiu Feng / The Continental extras not present in the vendor category map
EXTRA_CONTRACTOR = {
    "Black Cat": "Jiu Feng",
    "The Ukrainian Prisoner": "Jiu Feng",
    "Buluc's Mansion": "Jiu Feng",
    "Brooklyn 10-10": "The Continental",
    "The Yacht Heist": "The Continental",
    "Breakin' Feds": "The Continental",
    "Henry's Rock": "The Continental",
    "Hell's Island": "The Continental",
    "The White House": "The Continental",
    "Border Crossing": "The Continental",
    "Border Crystals": "The Continental",
    "Alaskan Deal": "The Continental",
    "Beneath the Mountain": "The Continental",
    "Brooklyn Bank": "The Continental",
    "San Martín Bank": "The Continental",
    "Breakfast in Tijuana": "The Continental",
    "Shacklethorne Auction": "The Continental",
    "Birth of Sky": "The Continental",
}
# Jiu Feng is the newest contractor: his heists supersede the wiki's "Vlad" tag
for k in ("Black Cat", "The Ukrainian Prisoner", "Buluc's Mansion"):
    contractor_of[k] = "Jiu Feng"

reg = {}
for name, cats in union.items():
    contractor = EXTRA_CONTRACTOR.get(name) or contractor_of.get(name, "?")
    mode = "both"
    classic = False
    for c in cats:
        if c in MODE_CATS:
            m = MODE_CATS[c]
            if mode == "both" or m != mode:
                mode = m if mode == "both" else ("both" if m != mode else mode)
        if c == "Classic heists":
            classic = True
    job = ""
    page = pages.get(name)
    if page:
        mh = find_templates(page, "MultipleHeist2")
        if mh and mh[0][2]:
            job = mh[0][2][0].strip()
    reg[name] = {
        "page": name,
        "name": name,
        "job": job,
        "contractor": contractor,
        "mode": "escape" if name in ESCAPES else mode,
        "classic": classic,
        "wiki": "https://payday.fandom.com/wiki/" + name.replace(" ", "_"),
    }

heists = [v for v in reg.values() if v["mode"] != "escape"]
escapes = [v for v in reg.values() if v["mode"] == "escape"]

print("ВСЕГО записей:", len(reg))
print("  хайстов:", len(heists), "| побеги:", len(escapes))
from collections import Counter
print("  по контрактору:", Counter(v["contractor"] for v in heists).most_common())
print("  по режиму:", Counter(v["mode"] for v in heists))
print("  классические:", sum(1 for v in heists if v["classic"]))
print("  без контрактора:", [v["name"] for v in heists if v["contractor"] == "?"])

json.dump({"heists": heists, "escapes": escapes},
          open("payday/data/heist_registry.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)