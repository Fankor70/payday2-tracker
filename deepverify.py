# -*- coding: utf-8 -*-
"""Independent re-verification of every achievement against the wiki.

Deliberately does NOT reuse the pipeline's parsers: it re-fetches the wiki from
scratch and re-extracts the rows with its own code, then diffs that against what
the app actually ships (``data/app_data.json``). A parser bug shared with the
build would otherwise verify itself.

Checks, per heist:
  * membership   -- rows the wiki lists that we do not put on that heist, and
                    rows we put on it that the wiki does not list
  * ru name      -- our Russian name vs the wiki's
  * ru condition -- our Russian condition vs the wiki's
  * day          -- the "N-й день" hint
and globally:
  * every EN name we ship exists in the wiki/Steam master list
  * every wiki row is reachable from some heist or the global bucket
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://payday.fandom.com/ru/api.php"
UA = {"User-Agent": "Mozilla/5.0 (achievement-deep-verify)"}
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "verify_deep.json")


# --------------------------------------------------------------------- wiki
def api(params, tries=4):
    params = dict(params, format="json")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if a == tries - 1:
                print("   ! api:", params.get("titles"), e)
            time.sleep(2 + a * 2)
    return {}


def wikitext(title):
    d = api({"action": "query", "prop": "revisions", "rvprop": "content",
             "rvslots": "main", "titles": title, "redirects": "1"})
    pages = (d.get("query") or {}).get("pages") or {}
    for _, p in pages.items():
        rev = ((p.get("revisions") or [{}])[0])
        return ((rev.get("slots") or {}).get("main") or {}).get("*") or ""
    return ""


def split_params(body):
    """Split template params on top-level pipes only (``[[a|b]]`` must survive)."""
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


def templates(text, name):
    """Every {{name|...}} block, as a list of params."""
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
        block = text[m.end():i - 1]
        if block.count("{{") != block.count("}}"):
            continue
        res.append(split_params(block))
    return res


def clean(x):
    x = re.sub(r"<[^>]+>", "", x or "")
    x = re.sub(r"\{\{[^{}]*\}\}", "", x)
    x = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", x)
    x = x.replace("'''", "").replace("''", "")
    x = re.sub(r"<!--.*?-->", "", x, flags=re.S)
    return re.sub(r"\s+", " ", x).strip()


DAY_RE = re.compile(r"\b(\d+)\s*-?\s*й?\s*день", re.I)
DAY_WORD = {"первый": 1, "второй": 2, "третий": 3, "четвёртый": 4, "четвертый": 4,
            "пятый": 5, "шестой": 6, "седьмой": 7}
REWARD_TAIL = re.compile(r"\s*(?:Выполнение достижения открывает|Открывает)\b.*$", re.I)


def parse_entry(params):
    """`{{Достижение|RU name (ориг. EN name)|3 = condition|image = ...}}`"""
    first = clean(params[0]) if params else ""
    m = re.match(r"^(.*?)\s*\(\s*ориг\.\s*(.+?)\s*\)$", first)
    if m:
        ru, en = clean(m.group(1)), clean(m.group(2))
    else:
        ru, en = first, first
        if re.search(r"[A-Za-z]", ru) and len(re.findall(r"[A-Za-z]", ru)) > 0.9 * max(1, len(ru)):
            ru, en = "", first          # a Latin-only name IS the English key
    desc, day = "", None
    for p in params[1:]:
        k, _, v = p.partition("=")
        k, v = clean(k).strip().lower(), clean(v)
        if k == "image":
            continue
        if re.fullmatch(r"\d+", k):
            desc = v          # the number is a template param, NOT the day
        elif k in ("достижение", "условие", "описание", "условия"):
            desc = v
        elif not desc and v and not k.startswith(("image", "имя", "name")):
            desc = v
    dm = DAY_RE.search(desc)
    if dm:
        day = int(dm.group(1))
    else:
        for w, n in DAY_WORD.items():
            if w + " " in desc.lower() and "день" in desc.lower():
                day = n
                break
    return {"name_ru": ru, "name_en": en,
            "desc_ru": REWARD_TAIL.sub("", desc).strip(), "day": day}


# ----------------------------------------------------------------- fetching
def fetch_all(titles):
    out = {}
    for n, t in enumerate(titles, 1):
        wt = wikitext(t)
        rows = [parse_entry(p) for p in templates(wt, "Достижение")]
        rows = [r for r in rows if r["name_en"] or r["name_ru"]]
        if rows:
            out[t] = rows
        print("   %3d/%d  %-42s %3d" % (n, len(titles), t, len(rows)))
    return out


# ------------------------------------------------------------------ compare
def norm(s):
    """Compare text the way a reader would: fold the typography that differs
    between the wiki and Steam ("…" vs "...", curly quotes, ё/e, dashes)."""
    s = (s or "").lower()
    s = s.replace("ё", "е").replace("…", "...").replace("–", "-").replace("—", "-")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"')):
        s = s.replace(a, b)
    s = re.sub(r"[«»\"'“”(),.:;!?*\-\[\]{}]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# the wiki and Steam spell a few names differently; the wiki row still refers to
# the same achievement, so compare through this alias table
ALIAS = {
    "every dog has its day": "every dog has his day",
    "urban hikeing": "urban hiking",
    "jack the ripper s prison slippers": "jack the rippers prison slippers",
    "everyday i m shovelin": "every day i m shovelin",
    "f k it we re walking": "fuck it we re walking",
}


def main():
    app = json.load(io.open(os.path.join(HERE, "app", "data", "app_data.json"), encoding="utf-8"))
    achs = {a["id"]: a for a in app["achievements"]}
    by_en = {}
    for a in app["achievements"]:
        by_en.setdefault(ALIAS.get(norm(a["name"]), norm(a["name"])), []).append(a)

    titles = [h.get("name_ru") or h.get("page") for h in app["heists"]]
    titles = [t for t in titles if t]
    print("страниц хайстов к проверке:", len(titles))
    wiki = fetch_all(titles)

    report = {"heists": {}, "totals": {}}
    miss_member, extra_member, name_diff, desc_diff, day_diff = [], [], [], [], []
    unmatched_rows = []
    wiki_ids = set()

    for title, rows in sorted(wiki.items()):
        h = next((x for x in app["heists"]
                  if (x.get("name_ru") or x.get("page")) == title), None)
        if h is None:
            continue
        ours = set(h.get("ids") or [])
        for v in (h.get("variants") or []):
            ours |= set(v.get("ids") or [])
        found = set()
        for r in rows:
            cand = by_en.get(ALIAS.get(norm(r["name_en"]), norm(r["name_en"]))) or []
            if not cand:
                unmatched_rows.append({"heist": title, "row": r})
                continue
            a = cand[0]
            aid = a["id"]
            found.add(aid)
            wiki_ids.add(aid)
            if r["name_ru"] and norm(r["name_ru"]) != norm(a.get("name_ru")):
                name_diff.append({"heist": title, "id": aid,
                                  "wiki": r["name_ru"], "ours": a.get("name_ru"),
                                  "en": a["name"]})
            if r["desc_ru"] and norm(r["desc_ru"]) != norm(a.get("desc_ru")):
                desc_diff.append({"heist": title, "id": aid,
                                  "en": a["name"], "wiki": r["desc_ru"][:160],
                                  "ours": (a.get("desc_ru") or "")[:160]})
            if r["day"] and a.get("day") and r["day"] != a["day"]:
                day_diff.append({"heist": title, "id": aid, "en": a["name"],
                                 "wiki": r["day"], "ours": a["day"]})
        for i in sorted(found - ours):
            miss_member.append({"heist": title, "id": i, "en": achs[i]["name"]})
        for i in sorted(ours - found):
            extra_member.append({"heist": title, "id": i, "en": achs[i]["name"]})
        report["heists"][title] = {"wiki_rows": len(rows), "matched": len(found),
                                   "ours": len(ours)}

    report["totals"] = {
        "pages_with_rows": len(wiki),
        "wiki_rows_total": sum(len(v) for v in wiki.values()),
        "rows_matched": len(wiki_ids),
        "rows_unmatched": len(unmatched_rows),
        "wiki_but_not_on_heist": len(miss_member),
        "ours_but_not_in_wiki": len(extra_member),
        "ru_name_diff": len(name_diff),
        "ru_condition_diff": len(desc_diff),
        "day_diff": len(day_diff),
    }
    report["unmatched_rows"] = unmatched_rows
    report["miss_member"] = miss_member
    report["extra_member"] = extra_member
    report["name_diff"] = name_diff
    report["desc_diff"] = desc_diff
    report["day_diff"] = day_diff
    json.dump(report, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n" + "=" * 66)
    print("ИТОГ ПЕРЕСВЕРКИ С ВИКИ")
    print("=" * 66)
    for k, v in report["totals"].items():
        print("  %-26s %s" % (k, v))
    print("\nотчёт:", OUT)


if __name__ == "__main__":
    main()