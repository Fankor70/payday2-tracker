import json, urllib.parse, urllib.request, time, re
API="https://payday.fandom.com/api.php"; UA={"User-Agent":"Mozilla/5.0"}
def api(p):
    p["format"]="json"
    req=urllib.request.Request(API+"?"+urllib.parse.urlencode(p), headers=UA)
    for a in range(4):
        try:
            with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode("utf-8"))
        except Exception as e: time.sleep(3)
    return {}
d=api({"action":"query","list":"categorymembers","cmtitle":"Category:PAYDAY 2 heists","cmlimit":500})
mem=[m["title"] for m in d["query"]["categorymembers"]]
arts=[t for t in mem if not t.startswith(("Category:","File:"))]
print("article-like:",len(arts))
pages={}
for i in range(0,len(arts),50):
    ch=arts[i:i+50]
    r=api({"action":"query","titles":"|".join(ch),"redirects":"1","prop":"revisions","rvprop":"content","rvslots":"main"})
    q=r.get("query",{})
    norm={n["to"]:n["from"] for n in q.get("normalized",[])}
    red={n["to"]:n["from"] for n in q.get("redirects",[])}
    for pid,p in q.get("pages",{}).items():
        revs=p.get("revisions")
        if not revs: continue
        full=p["title"]; key=red.get(full,norm.get(full,full))
        pages[key]=revs[0]["slots"]["main"]["*"]
    print("batch",i,"->",len(pages))
json.dump(pages,open("payday/data/heist_pages.json","w",encoding="utf-8"),ensure_ascii=False)
print("TOTAL",len(pages))
