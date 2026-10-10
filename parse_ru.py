# -*- coding: utf-8 -*-
"""Parse Russian wiki achievements and merge them onto the English dataset.

Russian template: {{Достижение|<рус название> (ориг. <english name>)|3 = <описание>|image = <файл>}}
The embedded "(ориг. ...)" is what lets us match RU rows to EN rows.
"""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")

from parse_ach import split_params, find_templates, clean


def strip_ru_links(s):
    return clean(s)


def parse_ru():
    master = open("payday/data/ru_master.wikitext", encoding="utf-8").read()
    sub = json.load(open("payday/data/ru_subpages.json", encoding="utf-8"))

    items = []

    def add(text, source):
        for (_s, _e, p) in find_templates(text, "Достижение"):
            if len(p) < 2:
                continue
            title = p[0].strip()
            body = ""
            for q in p[1:]:
                # numbered/named param: the description is "|3 = <text>"
                m = re.match(r"^\s*\w+\s*=\s*(.*)$", q, re.S)
                if m:
                    body = m.group(1)
                    break
            if not body:
                # fall back to the longest non-image param
                cands = [q for q in p[1:] if not q.strip().startswith(("image", "img"))]
                body = max(cands, key=len) if cands else ""
            en = None
            m = re.search(r"\(ориг\.\s*(.+?)\)\s*$", title, re.S)
            if m:
                en = m.group(1).strip()
                ru = title[:m.start()].strip()
            else:
                ru = title
            # a few wiki rows have a malformed template and swallow "|image = .jpg}}"
            body = re.split(r"\|\s*(?:image|img|file)\s*=", body)[0]
            body = body.rstrip("}").strip()
            items.append({
                "ru_name": ru,
                "en_name": en,
                "ru_desc": strip_ru_links(body),
                "ru_source": source,
            })

    add(master, "__master__")
    for k, v in sub.items():
        add(v, k)
    return items


ru = parse_ru()
print("RU achievements parsed:", len(ru))
print("  with embedded EN name:", sum(1 for x in ru if x["en_name"]))
print("  without:", sum(1 for x in ru if not x["en_name"]))

# ---- merge onto EN ------------------------------------------------------
en = json.load(open("payday/data/ach_final.json", encoding="utf-8"))
by_en = {}
for r in en:
    by_en.setdefault(r["name"].strip().lower(), r)

# RU titles are sometimes display-truncated with an ellipsis ("Let's Do Th…"),
# so fall back to a prefix match when the exact name misses.
names_sorted = sorted(by_en.keys(), key=len, reverse=True)


def resolve(key):
    if key in by_en:
        return by_en[key]
    probe = key.rstrip(".… ").strip()
    if len(probe) >= 6:
        for cand in names_sorted:
            if cand.startswith(probe[:max(6, len(probe) - 1)]):
                return by_en[cand]
    return None


matched, unmatched = 0, []
for x in ru:
    key = (x["en_name"] or x["ru_name"]).strip().lower()
    tgt = resolve(key)
    if tgt is not None and "name_ru" not in tgt:
        tgt["name_ru"] = x["ru_name"]
        tgt["desc_ru"] = x["ru_desc"]
        tgt["ru_source"] = x["ru_source"]
        matched += 1
    elif tgt is not None:
        matched += 1
    else:
        unmatched.append(x)

print("matched to EN:", matched, "| EN-only:", len(en) - matched, "| RU-only:", len(unmatched))
print()
print("RU-only samples:")
for x in unmatched[:15]:
    print("  -", x["ru_name"], "|", (x["en_name"] or "?"))

json.dump(ru, open("payday/data/ru_parsed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(en, open("payday/data/ach_merged.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(unmatched, open("payday/data/ru_only.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- coverage by heist --------------------------------------------------
sys.path.insert(0, "payday")
from heuristics import HEISTS
withru = sum(1 for r in en if r.get("name_ru"))
print("\nEN achievements now carrying RU text:", withru, "/", len(en))
srcs = {}
for r in en:
    if r.get("name_ru"):
        srcs[r["ru_source"]] = srcs.get(r["ru_source"], 0) + 1
print("RU coverage by page (top):")
for k, v in sorted(srcs.items(), key=lambda x: -x[1])[:12]:
    print(f"   {v:4d}  {k}")