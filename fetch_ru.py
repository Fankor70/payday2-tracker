# -*- coding: utf-8 -*-
"""Fetch Russian PAYDAY 2 achievement subpages (master already saved)."""
import json, re, urllib.parse, urllib.request, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://payday.fandom.com/ru/api.php"
UA = {"User-Agent": "Mozilla/5.0 (achievement-research)"}


def api(params):
    params["format"] = "json"
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print("   retry", a, repr(e)[:90]); time.sleep(3)
    return {}


master = open("payday/data/ru_master.wikitext", encoding="utf-8").read()
names = list(dict.fromkeys(re.findall(r"\{\{/([^}|]+)\}\}", master)))
print("RU subpages:", len(names))

BASE = "Достижения (PAYDAY 2)"
raw, missing = {}, []
for i in range(0, len(names), 40):
    chunk = names[i:i + 40]
    d = api({"action": "query", "titles": "|".join(BASE + "/" + n for n in chunk),
             "redirects": "1", "prop": "revisions", "rvprop": "content", "rvslots": "main"})
    q = d.get("query", {})
    norm = {n["to"]: n["from"] for n in q.get("normalized", [])}
    red = {n["to"]: n["from"] for n in q.get("redirects", [])}
    for pid, p in q.get("pages", {}).items():
        revs = p.get("revisions")
        full = p.get("title", "")
        key = red.get(full, norm.get(full, full)).replace(BASE + "/", "")
        if not revs:
            missing.append(key); continue
        raw[key] = revs[0]["slots"]["main"]["*"]
    print("batch", i, "->", len(raw), "ach:", sum(v.count("{{Achievement") for v in raw.values()))

json.dump(raw, open("payday/data/ru_subpages.json", "w", encoding="utf-8"), ensure_ascii=False)
print("TOTAL", len(raw), "MISSING", missing)