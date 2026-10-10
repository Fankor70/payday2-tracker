import json, re, urllib.parse, urllib.request, time, os
API="https://payday.fandom.com/api.php"; UA={"User-Agent":"Mozilla/5.0 (achievement-research)"}
def api(p):
    p["format"]="json"
    req=urllib.request.Request(API+"?"+urllib.parse.urlencode(p), headers=UA)
    for a in range(3):
        try:
            with urllib.request.urlopen(req,timeout=60) as r: return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(" retry",a,e); time.sleep(2)
raw=json.load(open("payday/data/subpages.json",encoding="utf-8"))
master=open("payday/data/pd2_achievements.wikitext",encoding="utf-8").read()
pages=list(dict.fromkeys(re.findall(r"\{\{/([^}|]+)\}\}", master)))
missing=[p for p in pages if p not in raw]
print("missing",len(missing))
for i in range(0,len(missing),25):
    ch=missing[i:i+25]
    d=api({"action":"query","titles":"|".join(ch),"redirects":"1","prop":"revisions","rvprop":"content","rvslots":"main"})
    q=d.get("query",{})
    norm={n["to"]:n["from"] for n in q.get("normalized",[])}
    red={n["to"]:n["from"] for n in q.get("redirects",[])}
    for pid,p in q.get("pages",{}).items():
        revs=p.get("revisions")
        if not revs:
            print("  STILL MISSING:", p.get("title")); continue
        txt=revs[0]["slots"]["main"]["*"]
        key=red.get(p["title"], norm.get(p["title"], p["title"]))
        raw[key]=txt
        print("  ok", key, "->", p["title"], len(txt))
json.dump(raw,open("payday/data/subpages.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("TOTAL",len(raw),"of",len(pages))
