# -*- coding: utf-8 -*-
"""Parse the Steam Global Achievements page into JSON (authoritative list)."""
import re, io, json, sys, html
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

t = io.open("payday/data/steam_ach.html", encoding="utf-8", errors="replace").read()

# each achievement is one .achieveRow block
blocks = re.split(r'<div class="achieveRow\s*"', t)[1:]
print("blocks:", len(blocks))

ACH_NAME = re.compile(r'<div class="achieveTxt">\s*<h3>(.*?)</h3>', re.S)
ACH_DESC = re.compile(r'<div class="achieveTxt">.*?<h5>(.*?)</h5>', re.S)
PCT = re.compile(r'class="achievePercent">(.*?)</div>', re.S)
IMG = re.compile(r'<img src="(https://[^"]+)"\s*width="64"', re.S)


def dehtml(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = s.replace(' ', ' ')
    return re.sub(r'\s+', ' ', s).strip()


out = []
for b in blocks:
    # stop at the next row boundary to avoid capturing the following row's text
    cut = b.find('<div class="achieveRow')
    if cut > 0:
        b = b[:cut]
    mn, md, mp, mi = ACH_NAME.search(b), ACH_DESC.search(b), PCT.search(b), IMG.search(b)
    if not mn:
        continue
    out.append({
        "name": dehtml(mn.group(1)),
        "desc": dehtml(md.group(1)) if md else "",
        "pct": dehtml(mp.group(1)) if mp else "",
        "img": mi.group(1) if mi else "",
    })

print("parsed:", len(out))
json.dump(out, open("payday/data/steam_parsed.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

names = [x["name"] for x in out]
print("уникальных имён:", len(set(n.lower() for n in names)))
print("с описанием:", sum(1 for x in out if x["desc"]))
print("с процентом:", sum(1 for x in out if x["pct"]))
print()
for x in out[:5]:
    print(" *", x["name"], "|", x["pct"], "|", x["desc"][:90])
print()
print("=== пример с наградой ===")
for x in out:
    if "Unlocks" in x["desc"]:
        print(" *", x["name"], "|", x["desc"][:160]); break