# -*- coding: utf-8 -*-
"""Pull the "Связанные достижения" section off every Russian heist article.

This is the authoritative per-heist achievement list on the RU wiki, and it is
far better than inferring attribution from English achievement text: the wiki
states which heist each row belongs to, and multi-day heists mark the day.
"""
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


def split_params(body):
    out, depth, link, cur = [], 0, 0, []
    i, n = 0, len(body)
    while i < n:
        if body.startswith("[[", i):
            link += 1; cur.append("[["); i += 2; continue
        if body.startswith("]]", i) and link:
            link -= 1; cur.append("]]"); i += 2; continue
        ch = body[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "|" and depth == 0 and link == 0:
            out.append("".join(cur)); cur = []
        else:
            cur.append(ch)
        i += 1
    out.append("".join(cur))
    return out


def find_templates(text, name):
    res = []
    for m in re.finditer(r"\{\{\s*" + re.escape(name) + r"\s*[|\}]", text):
        if text[m.end() - 1] == "}":
            continue
        i, depth = m.end(), 1
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        if depth == 0:
            res.append(split_params(text[m.end():i - 1]))
    return res


def strip_templates(s):
    """Unwrap {{color|class|text}} repeatedly; drop anything still malformed."""
    for _ in range(4):
        new = re.sub(r"\{\{[Cc][Oo][Ll][Oo][Rr]\|[^|{}]*\|([^{}]*)\}\}", r"\1", s)
        if new == s:
            break
        s = new
    return re.sub(r"\{\{[^{}]*\}\}", " ", s)


def clean(s):
    s = s.strip()
    s = strip_templates(s)
    s = re.sub(r"\[\[([^\|\]]*)\|([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'{2,}", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\xa0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def linked_section(txt):
    """Text between '== Связанные достижения ==' and the next '==' heading."""
    m = re.search(r"==+\s*Связанные\s*\[\[Достижения[^=]*==+", txt)
    if not m:
        return ""
    rest = txt[m.end():]
    nxt = re.search(r"\n==[^=]", rest)
    return rest[:nxt.start()] if nxt else rest[:20000]


WORD_DAY = {"первый": 1, "первом": 1, "первого": 1, "one": 1,
            "второй": 2, "втором": 2, "второго": 2, "two": 2,
            "третий": 3, "третьем": 3, "третьего": 3, "three": 3,
            "четвёртый": 4, "четвертый": 4, "четвёртом": 4, "четвертом": 4,
            "пятый": 5, "пятом": 5, "five": 5}

# "Достижение может быть получено в 3 дне контракта «Поджигатель»."
NOTE_DAY = re.compile(
    r"(Достижение может быть получ[её]но в\s+(\d+)\s*-?\s*дне)", re.I)
# "... в 3 дне ограбления", "во втором дне"
IN_DAY = re.compile(
    r"\bв(?:о)?\s+(\d+)\s*-?\s*дне\b|\bв(?:о)?\s+(" + "|".join(WORD_DAY) + r")\s+дне\b", re.I)
# "Выполняя третий день контракта", "Завершите второй день контракта"
DAY_WORD = re.compile(
    r"\b(" + "|".join(k for k in WORD_DAY if k.isalpha()) + r")\s+ден[ьяе]\b", re.I)
DAY_NUM = re.compile(r"\b(\d+)\s*-?\s*ден[ьяе]\b")


def detect_day(text):
    if not text:
        return None, ""
    note = ""
    m = NOTE_DAY.search(text)
    if m:
        note = m.group(0).strip()
        return int(m.group(2)), note
    m = IN_DAY.search(text)
    if m:
        return (int(m.group(1)) if m.group(1) else WORD_DAY[m.group(2).lower()]), ""
    m = DAY_WORD.search(text)
    if m:
        return WORD_DAY[m.group(1).lower()], ""
    m = DAY_NUM.search(text)
    if m:
        return int(m.group(1)), ""
    return None, ""


def parse_entries(section):
    out = []
    for p in find_templates(section, "Достижение"):
        title = p[0].strip()
        desc = ""
        for q in p[1:]:
            m = re.match(r"^\s*\w+\s*=\s*(.*)$", q, re.S)
            if m and m.group(1):
                desc = m.group(1)
                break
        en = None
        mm = re.search(r"\((?:ориг\.|англ\.)\s*(.+?)\)\s*$", title, re.S)
        if mm:
            en = mm.group(1).strip()
            ru = title[:mm.start()].strip()
        else:
            ru = title
        body = clean(desc)
        day, note = detect_day(body)
        out.append({
            "name_ru": clean(ru),
            "name_en": en,
            "desc_ru": body,
            "day": day,
            "note": note,
        })
    return out


# ---- fetch every RU heist article ------------------------------------------
heists = json.load(open("payday/data/ru_heists.json", encoding="utf-8"))
titles = [v["title"] for v in heists.values()]
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

json.dump(pages, open("payday/data/ru_heist_pages.json", "w", encoding="utf-8"), ensure_ascii=False)

out = {}
for meta in heists.values():
    txt = pages.get(meta["title"], "")
    sec = linked_section(txt)
    entries = parse_entries(sec) if sec else []
    key = (meta.get("name_en") or meta["title"])
    if entries:
        out[key] = {
            "title": meta["title"],
            "name_ru": meta.get("name_ru"),
            "count": len(entries),
            "entries": entries,
        }

json.dump(out, open("payday/data/ru_linked.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("\nхостов со списком связанных достижений:", len(out))
tot = sum(v["count"] for v in out.values())
print("всего записей в списках:", tot)
named = sum(1 for v in out.values() for e in v["entries"] if e["name_en"])
print("из них с оригинальным EN-именем:", named)
print("с указанием дня:", sum(1 for v in out.values() for e in v["entries"] if e["day"]))
print("с отдельной пометкой:", sum(1 for v in out.values() for e in v["entries"] if e.get("note")))
print()
for k in list(out)[:8]:
    v = out[k]
    print(f"  {k[:30]:32s} {v['count']:3d}")
print()
print("--- пример с указанием дня ---")
for v in out.values():
    for e in v["entries"]:
        if e["day"]:
            print(f"  [{v['title']} день {e['day']}] {e['name_ru']} ({e['name_en']})")
            break
    else:
        continue
    break