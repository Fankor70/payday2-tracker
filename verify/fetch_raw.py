import json, urllib.parse, urllib.request, time, sys, os

API = "https://payday.fandom.com/ru/api.php"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_heists.json")
CAT = "Категория:Ограбления PAYDAY 2"


def api(**params):
    params.setdefault("format", "json")
    params.setdefault("action", "query")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "pdkd-verify/1.0 (research)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            sys.stderr.write("retry %d %s\n" % (attempt, e))
            time.sleep(2 + attempt * 2)
    raise SystemExit("api failed")


# 1. category members
members = []
cont = {}
while True:
    d = api(list="categorymembers", cmtitle=CAT, cmlimit=500, **cont)
    for m in d.get("query", {}).get("categorymembers", []):
        if m["ns"] == 0:
            members.append(m["title"])
    if "continue" in d:
        cont = d["continue"]
    else:
        break
sys.stderr.write("category: %d\n" % len(members))
json.dump(members, open(os.path.join(os.path.dirname(OUT), "cat_titles.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# 2. batch revisions
pages = {}
titles = members
for i in range(0, len(titles), 40):
    chunk = titles[i:i + 40]
    d = api(prop="revisions", rvprop="content", rvslots="main", titles="|".join(chunk))
    q = d.get("query", {})
    for p in q.get("pages", {}).values():
        if "revisions" in p:
            pages[p["title"]] = p["revisions"][0]["slots"]["main"]["*"]
        else:
            sys.stderr.write("MISSING: %s\n" % p.get("title"))
    sys.stderr.write("fetched %d/%d\n" % (min(i + 40, len(titles)), len(titles)))
    time.sleep(1)

json.dump(pages, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
sys.stderr.write("saved %d pages\n" % len(pages))