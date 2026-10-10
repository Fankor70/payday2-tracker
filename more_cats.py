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
cats=["Basic heists","Classic heists","Stealth Heists","Loud-Only Heists","Escapes",
      "Heists contracted by Jiu Feng","Heists contracted by Bain","Heists contracted by The Dentist"]
union={}
for c in cats:
    d=api({"action":"query","list":"categorymembers","cmtitle":"Category:"+c,"cmlimit":500})
    m=[x["title"] for x in d.get("query",{}).get("categorymembers",[]) if not x["title"].startswith(("Category:","File:"))]
    print(f"== {c}: {len(m)}")
    for t in m:
        print("     ",t); union.setdefault(t,[]).append(c)
print("\nUNION:",len(union))
json.dump(union,open("payday/data/heist_union.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
