# -*- coding: utf-8 -*-
"""Self-check for the achievement dataset and the live counts.

Answers the question the tracker must never get wrong: "is this number right?"
Three independent layers are cross-checked:
  * field integrity  -- every row has usable EN/RU text, a category, sane ids
  * source agreement -- Steam (the game's own strings) vs the RU wiki's
    per-heist lists vs the EN wiki achievement pages
  * arithmetic       -- the totals the UI shows must equal what the rows say
"""
import json, os, re, sys, io, unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def norm(s):
    s = unicodedata.normalize("NFKD", (s or ""))
    s = s.replace("’", "'").replace("–", "-").replace(" ", " ")
    s = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()
    return re.sub(r"\s+", " ", s)


class Report:
    def __init__(self):
        self.problems = []
        self.warnings = []
        self.facts = {}

    def bad(self, code, detail, count=None):
        self.problems.append({"code": code, "detail": detail,
                              "count": count if count is not None else 1})

    def warn(self, code, detail, count=None):
        self.warnings.append({"code": code, "detail": detail,
                              "count": count if count is not None else 1})

    def ok(self):
        return not self.problems


def run(progress=None):
    R = Report()
    data = json.load(open(os.path.join(DATA, "app_data.json"), encoding="utf-8"))
    A = data["achievements"]

    # ---------------------------------------------------- field integrity
    seen_ids = set()
    for a in A:
        n = a["id"]
        if n in seen_ids:
            R.bad("dup_id", "повторяется id", a["name"])
        seen_ids.add(n)
        for field in ("name", "desc"):
            if not str(a.get(field) or "").strip():
                R.bad("empty_field", "%s пусто" % field, a["name"])
        if not a.get("name_ru"):
            R.bad("no_ru_name", "нет русского названия", a["name"])
        if not a.get("desc_ru"):
            R.bad("no_ru_desc", "нет русского описания", a["name"])
        if not a.get("category"):
            R.bad("no_category", "нет категории", a["name"])
        for label, pat in (("wiki_link", r"\[\[|\]\]"), ("template", r"\{\{|\}\}"),
                           ("pipe", r"\|"), ("bold", r"'{2,}"), ("tag", r"<[^>]+>"),
                           ("nbsp", r"&nbsp;| ")):
            if re.search(pat, str(a.get("desc") or "")):
                R.bad("en_junk:" + label, "мусор в английском описании", a["name"])
            if re.search(pat, str(a.get("desc_ru") or "")):
                R.bad("ru_junk:" + label, "мусор в русском описании", a["name"])
        if a.get("pct") is not None and not (0 <= a["pct"] <= 100):
            R.bad("pct_range", "процент вне 0..100", a["name"])

    names = Counter(norm(a["name"]) for a in A)
    dupes = [k for k, v in names.items() if v > 1 and k]
    if dupes:
        R.bad("dup_name", "дубли названий: " + ", ".join(dupes[:5]), len(dupes))

    # ------------------------------------------------- source agreement
    try:
        steam = {norm(a["name"]) for a in A}
        linked = json.load(open(os.path.join(os.path.dirname(HERE),
                                               "data", "ru_linked.json"),
                                encoding="utf-8"))
        wiki_names, heist_lists = set(), {}
        for key, v in linked.items():
            for e in v["entries"]:
                if e.get("name_en"):
                    n = norm(e["name_en"])
                    wiki_names.add(n)
                    heist_lists.setdefault(n, set()).add(key)
        only_steam = steam - wiki_names
        only_wiki = wiki_names - steam
        R.facts["wiki_listed"] = len(wiki_names)
        R.facts["in_steam_not_in_wiki_lists"] = len(only_steam)
        R.facts["in_wiki_lists_not_in_steam"] = len(only_wiki)
        if only_wiki:
            R.warn("wiki_only", "есть на вики, но нет в списке достижений: "
                                + ", ".join(sorted(only_wiki)[:5]), len(only_wiki))
    except FileNotFoundError:
        R.warn("no_wiki", "нет файла списков вики — сверка источников пропущена")

    # -------------------------------------------------------- arithmetic
    total = len(A)
    R.facts["total"] = total

    glob = set(data.get("global_ids") or [])
    # the contractor ladders live in their own bucket, not in "общие"
    glob |= set((data.get("route_meta") or {}).get("ladders") or [])
    heist_union = set()
    for h in data["heists"]:
        heist_union |= set(h["ids"])
        for v in (h.get("variants") or []):
            heist_union |= set(v["ids"])
    unaccounted = set(seen_ids) - heist_union - glob
    R.facts["assigned_to_heists"] = len(heist_union)
    R.facts["global"] = len(glob)
    R.facts["unaccounted"] = len(unaccounted)
    if unaccounted:
        R.bad("unaccounted", "достижения без хайста и без глобальных",
              len(unaccounted))

    for h in data["heists"]:
        bad = [i for i in h["ids"] if i not in seen_ids]
        if bad:
            R.bad("heist_bad_ids", "%s ссылается на несуществующие id" % h["page"],
                  len(bad))
        for v in (h.get("variants") or []):
            bad = [i for i in v["ids"] if i not in seen_ids]
            if bad:
                R.bad("variant_bad_ids",
                      "%s/%s — несуществующие id" % (h["page"], v["ru"]), len(bad))
            # a variant must not claim achievements its sibling also claims
            siblings = [(w["ru"], set(w["ids"])) for w in h["variants"] if w is not v]
            for rname, rids in siblings:
                if set(v["ids"]) & rids:
                    R.warn("variant_overlap",
                           "%s и %s пересекаются на %d"
                           % (v["ru"], rname, len(set(v["ids"]) & rids)))

    par = data.get("parallel") or {}
    par_ids = set()
    for v in par.values():
        par_ids |= set(v)
    par_ids |= set((data.get("route_meta") or {}).get("ladders") or [])
    if not par_ids <= seen_ids:
        R.bad("parallel_ids", "параллельные содержат чужие id",
              len(par_ids - seen_ids))
    if par_ids & heist_union:
        R.warn("parallel_heist_overlap",
               "достижение одновременно в хайсте и в параллельных",
               len(par_ids & heist_union))

    # ------------------------------------------------------------ progress
    if progress is not None:
        done = set(progress)
        R.facts["progress"] = len(done)
        R.facts["progress_pct"] = round(len(done) / total * 100, 1) if total else 0
        stray = done - seen_ids
        R.facts["progress_unknown"] = len(stray)
        if stray:
            R.warn("progress_unknown",
                   "в прогрессе есть id, которых нет в базе", len(stray))
        # per-heist counts the UI will show
        counts = {h["page"]: len(set(h["ids"]) & done) for h in data["heists"]}
        R.facts["heists_with_progress"] = sum(1 for v in counts.values() if v)
        R.facts["heists_total_ach"] = sum(len(h["ids"]) for h in data["heists"])
        R.facts["heists_untouched"] = sum(1 for v in counts.values() if v == 0)

    return R


def main():
    prog = None
    p = os.path.join(HERE, "progress.json")
    if os.path.exists(p):
        try:
            prog = set(json.load(open(p, encoding="utf-8")).get("done") or [])
        except Exception:                              # noqa: BLE001
            pass
    R = run(prog)
    print("=" * 68)
    print("ПРОВЕРКА ДАННЫХ")
    print("=" * 68)
    for k, v in R.facts.items():
        print(f"   {k:38s} {v}")
    print()
    if R.problems:
        print("ОШИБКИ —", len(R.problems))
        for p_ in R.problems[:20]:
            print("   [%s] %s — %s" % (p_["code"], p_["detail"], p_["count"]))
    else:
        print("ОШИБОК НЕТ")
    if R.warnings:
        print("предупреждения —", len(R.warnings))
        for p_ in R.warnings[:20]:
            print("   [%s] %s — %s" % (p_["code"], p_["detail"], p_["count"]))
    return 0 if R.ok() else 1


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.exit(main())