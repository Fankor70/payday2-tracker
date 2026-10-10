import json, urllib.parse, urllib.request, time
API="https://payday.fandom.com/api.php"; UA={"User-Agent":"Mozilla/5.0"}
def api(p):
    p["format"]="json"
    req=urllib.request.Request(API+"?"+urllib.parse.urlencode(p), headers=UA)
    for a in range(4):
        try:
            with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode("utf-8"))
        except Exception as e: time.sleep(3)
    return {}
found=set(); cont=None
for i in range(12):
    p={"action":"query","list":"search","srsearch":'insource:"MultipleHeist2"',"srlimit":500}
    if cont: p["srcontinue"]=cont
    d=api(p)
    for r in d.get("query",{}).get("search",[]):
        if r["ns"]==0: found.add(r["title"])
    cont=d.get("continue",{}).get("srcontinue")
    print("batch",i,len(found))
    if not cont: break
print("TOTAL",len(found))
json.dump(sorted(found),open("payday/data/heist_candidates.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
for x in sorted(found): print("  ",x)
