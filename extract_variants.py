# -*- coding: utf-8 -*-
"""Extract heist variants (Bank Heist money/safes/gold/random, Transport maps...)."""
import json, re, sys, io, urllib.parse, urllib.request, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API_RU = "https://payday.fandom.com/ru/api.php"
API_EN = "https://payday.fandom.com/api.php"
UA = {"User-Agent": "Mozilla/5.0 (variant-extractor)"}


def api(base, params):
    params["format"] = "json"
    req = urllib.request.Request(base + "?" + urllib.parse.urlencode(params), headers=UA)
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(3)
    return {}


def strip_wiki(t):
    t = re.sub(r"\{\{[^{}]*\}\}", " ", t)
    t = re.sub(r"\[\[([^\|\]]*)\|([^\]]*)\]\]", r"\2", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = t.replace("\xa0", " ")
    return t


def variants_ru(txt):
    """'Ограбление имеет четыре разновидности' followed by a # list."""
    body = strip_wiki(txt)
    out = []
    m = re.search(r"разновидност\w*|вариант\w*|разновидн\w*", body, re.I)
    if not m:
        return out
    tail = body[m.end(): m.end() + 400]
    # numbered list, allowing stray prose on the first line
    items = re.findall(r"^\s*#\s*([^\n#]{2,60})\s*$", tail, re.M)
    for it in items:
        it = it.strip().strip("*").strip()
        if it and it not in out:
            out.append(it)
    return out if len(out) > 1 else []


def variants_en(txt):
    """'There are 5 Armored transport heists, [[A]], [[B]], ...' plus tab lists."""
    body = strip_wiki(txt)
    out = []
    m = re.search(r"There (?:are|is)\s+(\d+)[^.]*?\b(?:heists?|variants?|versions?|maps?|levels?)\b[^.]*?:?(.{0,500})", body, re.I)
    if m:
        tail = m.group(2)
        for name in re.findall(r"(?:Transport:\s*)?([A-Z][A-Za-z'’\-]{2,20})", tail):
            name = name.strip()
            if name.lower() in ("heists", "variants", "versions", "maps", "levels", "the"):
                continue
            if name not in out:
                out.append(name)
        out = out[: int(m.group(1))]
    if len(out) > 1:
        return out
    # tab lists: {{Description3|tab2=Park|tab3=Downtown|...}}
    tabs = []
    for blk in re.findall(r"\{\{Description\d*\|(.*?)\}\}", txt, re.S):
        for k, v in re.findall(r"tab(\d+)\s*=\s*([^|]+)", blk):
            tabs.append((int(k), v.strip()))
        for k, v in re.findall(r"desc(\d+)\s*=", blk):
            pass
    tabs = [v for _k, v in sorted(tabs) if v.lower() != "general"]
    return tabs if len(tabs) > 1 else []


# ---- RU ----
ru_articles = json.load(open("payday/data/ru_heists.json", encoding="utf-8"))
ru_raw = {}
titles = [v["title"] for v in ru_articles.values()]
for i in range(0, len(titles), 30):
    d = api(API_RU, {"action": "query", "titles": "|".join(titles[i:i + 30]),
                     "redirects": "1", "prop": "revisions", "rvprop": "content", "rvslots": "main"})
    q = d.get("query", {})
    red = {n["to"]: n["from"] for n in q.get("redirects", [])}
    for pid, p in q.get("pages", {}).items():
        revs = p.get("revisions")
        if revs:
            ru_raw[red.get(p["title"], p["title"])] = revs[0]["slots"]["main"]["*"]
print("RU raw fetched:", len(ru_raw))

out = {}
for title, v in ru_articles.items():
    txt = ru_raw.get(title, "")
    vs = variants_ru(txt)
    if vs:
        out[v["name_en"] or title] = {"ru": vs, "title": title}

# ---- EN ----
en_pages = json.load(open("payday/data/heist_pages.json", encoding="utf-8"))
for title, txt in en_pages.items():
    vs = variants_en(txt)
    if vs:
        out.setdefault(title, {"en": vs})

print("\nХайсты с разновидностями:", len(out))
for k in sorted(out):
    v = out[k]
    ru = v.get("ru") or []
    en = v.get("en") or []
    print(f"  {k[:34]:36s} RU={ru} EN={en}")

json.dump(out, open("payday/data/variants.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)