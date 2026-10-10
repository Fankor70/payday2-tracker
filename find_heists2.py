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
for tmpl in ["Template:MultipleHeist2","MultipleHeist2"]:
    found=set(); cont=None
    for i in range(10):
        p={"action":"query","list":"backlinks","bltitle":tmpl,"blnamespace":0,"bllimit":500}
        if cont: p["blcontinue"]=cont
        d=api(p)
        for r in d.get("query",{}).get("backlinks",[]): found.add(r["title"])
        cont=d.get("continue",{}).get("blcontinue")
        if not cont: break
    print("==",tmpl,len(found))
    if found:
        json.dump(sorted(found),open("payday/data/heist_candidates.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
        for x in sorted(found): print("   ",x)
        break
