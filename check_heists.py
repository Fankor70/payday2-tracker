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
for t in ["Downtown","Flash Drive","Get the Coke","No Mercy (Payday 2)","Lab Rats","Meltdown"]:
    d=api({"action":"query","titles":t,"prop":"revisions","rvprop":"content","rvslots":"main","redirects":"1"})
    for pid,p in d.get("query",{}).get("pages",{}).items():
        revs=p.get("revisions")
        print("==",t,"->",p.get("title"),"MISSING" if not revs else len(revs[0]["slots"]["main"]["*"]))
        if revs:
            b=revs[0]["slots"]["main"]["*"]
            m=re.search(r"'''(.+?)'''\s*(?:is|are|was|were)", b)
            print("     ", (m.group(0)[:180] if m else re.sub(r"\s+"," ",b[:160])))
