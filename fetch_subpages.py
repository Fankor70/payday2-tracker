import json, re, urllib.parse, urllib.request, time, os

API = "https://payday.fandom.com/api.php"
UA = {"User-Agent": "Mozilla/5.0 (achievement-research)"}

def api(params):
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print("  retry", attempt, e)
            time.sleep(2)
    return None

master = open("payday/data/pd2_achievements.wikitext", encoding="utf-8").read()
pages = re.findall(r"\{\{/([^}|]+)\}\}", master)
pages = list(dict.fromkeys(pages))
print("unique subpages:", len(pages))

os.makedirs("payday/data/subpages", exist_ok=True)
raw = {}
for i in range(0, len(pages), 50):
    chunk = pages[i:i+50]
    d = api({"action": "query", "titles": "|".join(chunk), "prop": "revisions", "rvprop": "content", "rvslots": "main"})
    if not d: continue
    for pid, p in d["query"]["pages"].items():
        if pid == "-1":
            print("  MISSING:", p.get("title")); continue
        try:
            raw[p["title"]] = p["revisions"][0]["slots"]["main"]["*"]
        except Exception as e:
            print("  ERR", p.get("title"), e)
    print("fetched batch", i, "->", len(raw))

json.dump(raw, open("payday/data/subpages.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TOTAL", len(raw), "size", os.path.getsize("payday/data/subpages.json"))
