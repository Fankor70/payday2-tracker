# -*- coding: utf-8 -*-
"""Fetch Russian heist articles: name, original EN name, description."""
import json, re, sys, io, urllib.parse, urllib.request, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://payday.fandom.com/ru/api.php"
UA = {"User-Agent": "Mozilla/5.0 (achievement-research)"}


def api(params):
    params["format"] = "json"
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(3)
    return {}


d = api({"action": "query", "list": "categorymembers",
         "cmtitle": "Категория:Ограбления PAYDAY 2", "cmlimit": 500})
titles = [m["title"] for m in d.get("query", {}).get("categorymembers", [])
          if not m["title"].startswith(("Категория:", "Файл:"))]
print("русских статей:", len(titles))

pages = {}
for i in range(0, len(titles), 30):
    d = api({"action": "query", "titles": "|".join(titles[i:i + 30]),
             "redirects": "1", "prop": "revisions", "rvprop": "content", "rvslots": "main"})
    q = d.get("query", {})
    red = {n["to"]: n["from"] for n in q.get("redirects", [])}
    for pid, p in q.get("pages", {}).items():
        revs = p.get("revisions")
        if not revs:
            continue
        pages[red.get(p["title"], p["title"])] = revs[0]["slots"]["main"]["*"]
    print("batch", i, "->", len(pages))

out = {}
for title, txt in pages.items():
    # the lead line carries the name plus either "(ориг. X)" or "(англ. X)"
    head = txt.split("==")[0]
    head = head.replace("'''", " ")
    m = re.search(r"\(\s*(?:ориг\.|англ\.)\s*([^)]+)\)", head)
    name_en = m.group(1).strip() if m else None
    # name = text between the navbox and that parenthetical (or the em dash)
    body = head
    if m:
        body = head[:m.start()]
    body = re.sub(r"\{\{[^{}]*\}\}", " ", body)
    body = re.sub(r"\[\[[^\]]*\]\]", " ", body)
    body = body.strip().strip("—–-").strip()
    name_ru = body or title
    # the wiki title is the cleanest name when the lead line is noisy
    if (len(name_ru) < 2 or name_ru.count("(") != name_ru.count(")")
            or "{{" in name_ru or "}}" in name_ru or "|" in name_ru):
        name_ru = title
    if name_en:
        # keep apostrophes: "Breakin' Feds" must not become "Breakin"
        name_en = re.split(r'["\)—–]', name_en)[0].strip() or None
    d2 = re.search(r"==\s*Описание\s*==\s*\n(.+?)(?=\n==)", txt, re.S)
    desc = re.sub(r"\[\[([^\|\]]*)\|([^\]]*)\]\]", r"\2", d2.group(1)) if d2 else ""
    desc = re.sub(r"\[\[([^\]]*)\]\]", r"\1", desc)
    desc = re.sub(r"'{2,}", "", desc)
    desc = re.sub(r"\s+", " ", desc).strip()
    out[title] = {"title": title, "name_ru": name_ru, "name_en": name_en, "desc": desc[:400]}

json.dump(out, open("payday/data/ru_heists.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("сохранено:", len(out))
print("с оригинальным EN-именем:", sum(1 for v in out.values() if v["name_en"]))
print("с описанием:", sum(1 for v in out.values() if v["desc"]))
print()
for t in list(out)[:12]:
    v = out[t]
    print(f"  {v['name_ru'][:26]:28s} ← {str(v['name_en'])[:30]:32s} | {v['desc'][:50]}")