# -*- coding: utf-8 -*-
"""Fetch Template:Infobox Heist/<job> for every heist -> contractor, mode, days."""
import json, re, sys, io, urllib.parse, urllib.request, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from wikitools import find_templates

API = "https://payday.fandom.com/api.php"
UA = {"User-Agent": "Mozilla/5.0 (achievement-research)"}


def api(params):
    params["format"] = "json"
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(3)
    return {}


reg = json.load(open("payday/data/heist_registry.json", encoding="utf-8"))
items = reg["heists"] + reg["escapes"]
jobs = []
for v in items:
    j = v.get("job") or ""
    if j and j not in jobs:
        jobs.append(j)
print("infobox templates to fetch:", len(jobs))

found = {}
for i in range(0, len(jobs), 50):
    chunk = jobs[i:i + 50]
    titles = ["Template:Infobox Heist/" + j for j in chunk]
    d = api({"action": "query", "titles": "|".join(titles), "redirects": "1",
             "prop": "revisions", "rvprop": "content", "rvslots": "main"})
    q = d.get("query", {})
    red = {n["to"]: n["from"] for n in q.get("redirects", [])}
    for pid, p in q.get("pages", {}).items():
        full = p.get("title", "")
        job = full.split("Template:Infobox Heist/")[-1]
        job = red.get(full, job)
        revs = p.get("revisions")
        if not revs:
            continue
        f = {}
        for q2 in find_templates(revs[0]["slots"]["main"]["*"], "Infobox Heist"):
            for prm in q2[2]:
                if "=" in prm:
                    k, v2 = prm.split("=", 1)
                    f[k.strip().lower()] = v2.strip()
        found[job] = f
    print("batch", i, "->", len(found))

json.dump(found, open("payday/data/infoboxes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TOTAL", len(found))
from collections import Counter
print("contract ids:", Counter(v.get("contract", "?") for v in found.values()).most_common())
print("sample:", list(found.items())[0] if found else None)