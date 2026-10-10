# -*- coding: utf-8 -*-
"""Flag every achievement that needs a full four-player crew.

Three sources are merged, because no single one is complete:
  * the EN heist pages' inline tables  (long text, spells the requirement out)
  * the EN achievement subpages        (covers heists whose page has no table)
  * the RU per-heist linked lists     (Russian wording)
An achievement counts as crew-dependent if ANY source says so.
"""
import json, re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PAY = os.path.dirname(HERE)
sys.path.insert(0, PAY)
from heist_aliases import key_for, norm

TARGET = (sys.argv[1] if len(sys.argv) > 1
          else os.path.join(PAY, "data", "app_final.json"))
DATA = os.path.join(HERE, "data")
data = json.load(open(TARGET, encoding="utf-8"))
A = data["achievements"]

CREW4 = re.compile(
    r"full player lobby|full lobby|four[- ]man crew|4[- ]man crew|"
    r"all four players|with 4 players|with four players|"
    r"every (?:player|member) in the (?:lobby|crew)|all 4 characters|"
    r"each of the four|all four of you|"
    r"полным составом|вчетвером|все четверо|4 игрока|четыре игрока|"
    r"лобби из (?:четырёх|4)|каждый из четверых|всей командой",
    re.I)


def load(name):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


en_pages = load("en_heist_achievements.json")
ru = load("ru_linked.json")

# ------------------------------------------------ EN achievement subpages
from wikitools import clean as wiki_clean

sub_desc = {}
try:
    with open(os.path.join(PAY, "data", "subpages.json"), encoding="utf-8") as f:
        subpages = json.load(f)
    for page, txt in subpages.items():
        for m in re.finditer(r"\{\{Achievement\|([^|\n]+)\|[^|]*\|(.*?)\}\}", txt, re.S):
            sub_desc.setdefault(norm(m.group(1)), []).append(wiki_clean(m.group(2)))
except (OSError, KeyError) as e:
    print("подстраницы не прочитаны:", e)

ru_crew = set()
for key, v in ru.items():
    for e in v.get("entries", []):
        if e.get("name_en") and CREW4.search(e.get("desc_ru") or ""):
            ru_crew.add(norm(e["name_en"]))

by_norm = {}
for a in A:
    by_norm.setdefault(norm(a["name"]), a["id"])

marked = 0
for page, rows in en_pages.items():
    for r in rows:
        i = by_norm.get(norm(r["name"]))
        if i is not None and (r.get("crew4") or CREW4.search(r.get("desc") or "")):
            if not A[i].get("crew4"):
                marked += 1
            A[i]["crew4"] = True
            A[i]["crew4_source"] = "страница хайста: " + page

for key, aid in by_norm.items():
    if A[aid].get("crew4"):
        continue
    texts = sub_desc.get(key) or []
    if any(CREW4.search(t or "") for t in texts):
        A[aid]["crew4"] = True
        A[aid]["crew4_source"] = "подстраница достижений"
        marked += 1
    elif key in ru_crew:
        A[aid]["crew4"] = True
        A[aid]["crew4_source"] = "русская вики"
        marked += 1

LOOSE = re.compile(
    r"four man crew|4 man crew|each crew member|all days done|"
    r"кажд(ый|ого) из четверых|вчетвером|полным составом", re.I)
for a in A:
    if a.get("crew4"):
        continue
    if LOOSE.search((a.get("desc") or "") + " " + (a.get("desc_ru") or "")):
        a["crew4"] = True
        a["crew4_source"] = "текст достижения"
        marked += 1

json.dump(data, open(TARGET, "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print("записан:", TARGET)

print("страниц хайстов разобрано:", len(en_pages),
      "| строк:", sum(len(v) for v in en_pages.values()))
print("подстраниц достижений:", len(sub_desc))
print()
print("ОТМЕЧЕНО «НУЖЕН ПОЛНЫЙ СОСТАВ»:", marked)
print()
by_heist = {}
for a in A:
    if a.get("crew4"):
        hk = (a.get("heists") or ["(общее)"])[0]
        by_heist.setdefault(hk, []).append((a["name"], a.get("crew4_source", "")))
for hk in sorted(by_heist):
    print(" ", key_for(hk) if hk != "(общее)" else "(общее)", ":")
    for n, src in sorted(by_heist[hk]):
        print(f"     {n[:44]:46s} [{src}]")