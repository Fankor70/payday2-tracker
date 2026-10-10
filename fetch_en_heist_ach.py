# -*- coding: utf-8 -*-
"""Fetch the EN wiki's per-heist achievement tables and mine the crew requirement.

The heist pages carry the FULL achievement text, while Steam carries the short
in-game string. The long text is where "with a full player lobby" / "four man
crew" actually appears, so it is the better source for the crew flag.
"""
import json, os, re, sys, io, time, urllib.parse, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://payday.fandom.com/api.php"
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


def achievements_section(txt):
    """The '== Achievements ==' block of a heist page."""
    # the heading varies: plain '==Achievements==', '==[[Page|Achievements]]==',
    # and '==[[Page#Anchor|Achievements]] & [[Safehouse#Trophies|Trophies]]=='
    m = re.search(r"^==[^=\n]*\bAchievements\b[^=\n]*==", txt, re.I | re.M)
    if not m:
        return ""
    rest = txt[m.end():]
    nxt = re.search(r"\n==[^=]", rest)
    return rest[:nxt.start()] if nxt else rest[:20000]


def clean(s):
    s = s.strip()
    for _ in range(3):
        s = re.sub(r"\{\{[Cc]olor\|[^|{}]*\|([^{}]*)\}\}", lambda m: m.group(1), s)
    s = re.sub(r"\{\{[^{}]*\}\}", " ", s)
    s = re.sub(r"\[\[([^\|\]]*)\|([^\]]*)\]\]", lambda m: m.group(2), s)
    s = re.sub(r"\[\[([^\]]*)\]\]", lambda m: m.group(1), s)
    s = re.sub(r"'{2,}", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\xa0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


CREW4 = re.compile(
    r"full player lobby|four[- ]man crew|4[- ]man crew|all four players|"
    r"with 4 players|with four players|every player in the lobby|"
    r"each of the four|all 4 characters|полным составом|вчетвером|"
    r"все четверо|4 игрока|четыре игрока|lobby of 4", re.I)

data = json.load(open(os.path.join("app","data","app_data.json"), encoding="utf-8"))
pages = [h["page"] for h in data["heists"]]

raw = {}
for i in range(0, len(pages), 25):
    d = api({"action": "query", "titles": "|".join(pages[i:i + 25]),
             "redirects": "1", "prop": "revisions", "rvprop": "content",
             "rvslots": "main"})
    q = d.get("query", {})
    red = {n["to"]: n["from"] for n in q.get("redirects", [])}
    for pid, p in q.get("pages", {}).items():
        rv = p.get("revisions")
        if not rv:
            print("  нет страницы:", p.get("title"))
            continue
        full = p["title"]
        key = red.get(full, full)
        raw[key] = rv[0]["slots"]["main"]["*"]
    print("забрано", len(raw), "из", len(pages))

out, crew_found = {}, []
for page, txt in raw.items():
    sec = achievements_section(txt)
    if not sec:
        continue
    rows = []
    for p in find_templates(sec, "Achievement"):
        if len(p) < 3:
            continue
        nm, desc = clean(p[0]), clean(p[2])
        is4 = bool(CREW4.search(desc))
        rows.append({"name": nm, "desc": desc, "crew4": is4})
        if is4:
            crew_found.append((page, nm))
    if rows:
        out[page] = rows

json.dump(out, open(os.path.join("app","data","en_heist_achievements.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print()
print("страниц с таблицей достижений:", len(out))
print("всего строк:", sum(len(v) for v in out.values()))
print("требуют четверых:", len(crew_found))
for page, nm in crew_found:
    print(f"   {nm[:38]:40s} — {page}")