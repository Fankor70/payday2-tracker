import json, urllib.parse, urllib.request, time, re
API="https://payday.fandom.com/api.php"; UA={"User-Agent":"Mozilla/5.0"}
def api(p):
    p["format"]="json"
    req=urllib.request.Request(API+"?"+urllib.parse.urlencode(p), headers=UA)
    for a in range(4):
        try:
            with urllib.request.urlopen(req,timeout=120) as r: return json.loads(r.read().decode("utf-8"))
        except Exception as e: time.sleep(3)
    return {}
cands=["Masks (Payday 2)","Patterns","Materials","Suits (Payday 2)","Outfits (Payday 2)","Achievement Rewards"]
d=api({"action":"query","titles":"|".join(cands),"prop":"info","redirects":"1"})
titles=[]
for pid,p in d.get("query",{}).get("pages",{}).items():
    ok = 'MISSING' not in (p.get('missing') and 'MISSING' or '')
    print(p.get('title'), p.get('pageid'), 'MISSING' if p.get('missing') else '')
    if not p.get('missing'): titles.append(p['title'])
print("---")
d=api({"action":"query","titles":"|".join(titles),"prop":"revisions","rvprop":"content","rvslots":"main"})
out={}
for pid,p in d.get("query",{}).get("pages",{}).items():
    revs=p.get("revisions")
    if not revs: continue
    t=revs[0]["slots"]["main"]["*"]
    fn=p['title'].replace(" ","_").replace("/","_").replace("(","").replace(")","")
    open(f"payday/data/rewards_{fn}.wikitext","w",encoding="utf-8").write(t)
    out[p['title']]=len(t)
    print("saved",p['title'],len(t))
json.dump(out,open("payday/data/rewards_files.json","w",encoding="utf-8"),indent=1)
