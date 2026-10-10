# -*- coding: utf-8 -*-
"""Re-fetch ALL achievement subpages with the correct subpage prefix."""
import json, re, urllib.parse, urllib.request, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://payday.fandom.com/api.php"
UA = {"User-Agent": "Mozilla/5.0 (achievement-research)"}
BASE = "Achievements (Payday 2)"


def api(params):
    params["format"] = "json"
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print("   retry", a, repr(e)[:90])
            time.sleep(3)
    return {}


master = open("payday/data/pd2_achievements.wikitext", encoding="utf-8").read()
names = list(dict.fromkeys(re.findall(r"\{\{/([^}|]+)\}\}", master)))
print("subpages to fetch:", len(names))

raw = {}
missing = []
for i in range(0, len(names), 40):
    chunk = names[i:i + 40]
    titles = [BASE + "/" + n for n in chunk]
    d = api({"action": "query", "titles": "|".join(titles), "redirects": "1",
             "prop": "revisions", "rvprop": "content", "rvslots": "main"})
    q = d.get("query", {})
    norm = {n["to"]: n["from"] for n in q.get("normalized", [])}
    red = {n["to"]: n["from"] for n in q.get("redirects", [])}
    for pid, p in q.get("pages", {}).items():
        revs = p.get("revisions")
        full = p.get("title", "")
        key = red.get(full, norm.get(full, full)).replace(BASE + "/", "")
        if not revs:
            missing.append(key)
            continue
        txt = revs[0]["slots"]["main"]["*"]
        raw[key] = txt
        print("  ok %-34s -> %-44s %6d  ach=%d"
              % (key, full, len(txt), txt.count("{{Achievement")))
    print("batch done, have", len(raw))

json.dump(raw, open("payday/data/subpages.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nTOTAL", len(raw), "of", len(names), "| MISSING:", missing)