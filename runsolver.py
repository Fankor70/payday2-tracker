# -*- coding: utf-8 -*-
"""Minimum number of runs needed to complete every achievement of a heist.

Model: each achievement needs a difficulty floor and a set of run conditions.
A run at difficulty D with conditions C covers achievement A when
  rank(D) >= rank(A.min_diff)  and  A.conditions is a subset of C.
Minimum = greedy set cover over a candidate run pool. Repeated achievements
(find X five times) are counted separately as grind.
"""
import re
from itertools import combinations

DIFFS = ["easy", "normal", "hard", "very hard", "overkill", "mayhem",
         "death wish", "below zero", "death sentence"]
RANK = {d: i for i, d in enumerate(DIFFS)}

RU_DIFF = {
    "нормально": "normal", "сложно": "hard", "очень сложно": "very hard",
    "overkill": "overkill", "хаос": "mayhem", "жажда смерти": "death wish",
    "смертный приговор": "death sentence", "смертельный приговор": "death sentence",
    "ниже нуля": "below zero", "лёгко": "easy",
}

# name -> (regex on EN+RU text, human label, exclusive-with)
CONSTRAINTS = [
    ("no_alarm",
     r"without (?:having )?the alarm|without .{0,20}alarm|alarm (?:going off|go off)|"
     r"no alarm|without raising|never (?:raise|trigger)|"
     r"без (?:поднятия |подним )?тревог|тревог\w* не (?:подним|подним)|не подняв тревогу|"
     r"не поднимая тревог",
     "Без тревоги", []),
    ("no_civilians",
     r"without killing any civilians|no civilians|without killing a civilian|"
     r"не убив ни одного гражданского|не убивая гражданских|без убийства гражданских",
     "Не убивать гражданских", []),
    ("no_damage",
     r"without taking damage|without being (?:hit|shot)|untouched|"
     r"без получения урона|не получая урон",
     "Без урона", []),
    ("no_weapon",
     r"without using your primary weapon|without using a (?:primary|main) weapon|"
     r"without firing|без использования основного оружия|не стреляя из основного",
     "Без основного оружия", []),
    ("no_jump_grass",
     r"not jump(?:ing)? on the grass|without jumping|do not jump|"
     r"не прыгая на газон|прыгая на газон",
     "Не прыгать на газон", []),
    ("skyhook",
     r"skyhook|небесн\w+ крюк",
     "Все сумки через небесный крюк", ["sewer", "bags_tree"]),
    ("sewer",
     r"via the sewers?|through the sewer|"
     r"через канализаци|унеся все сумки с наличными через",
     "Все сумки через канализацию", ["skyhook", "bags_tree"]),
    ("bags_tree",
     r"(?:at least )?\d+ (?:body )?bags? under the Christmas tree|bags? (?:with bodies )?under the (?:Christmas )?tree|"
     r"сумки с телами под (?:Рождественскую )?елк",
     "4+ сумки под ёлку", ["sewer", "skyhook"]),
    ("bags_limit",
     r"carry only|carrying only|one bag|single bag|only one bag|"
     r"только одну сумк|несу только",
     "Ограничение по сумкам", ["skyhook", "sewer", "bags_tree"]),
    ("one_down",
     r"one ?down|модификатор\w* одного падения|одного падения",
     "Модификатор одного падения", []),
    ("stealth_only",
     r"\bin stealth\b|скрытн\w+ (?:подход|заход)|не поднимая тревоги",
     "Только скрытно", []),
    ("marker",
     r"leave a mark on|mark on the .*logo|оставьте знак на",
     "Отметка на объекте", []),
]

# "find the trophy five times" / "найдите статуэтку 5 раз" means real repetition.
# The negative lookahead keeps "4 разные маски" (four different masks) out.
REPEAT = re.compile(r"(\d+)\s+times?\b|(\d+)\s+раз(?!н)|\b(\d+)\s+раза\b", re.I)
# "on the OVERKILL difficulty or above" / "«Сложно» или выше" cascade: one run at a
# harder difficulty also satisfies the rung. Without it the heist must be run on
# that difficulty EXACTLY -- Safe House Nightmare's baby-mask achievements are the
# clear case, and they cost one run each.
OR_ABOVE = re.compile(r"or\s+(?:above|higher|more)|\bи\s+выше\b|или\s+выше", re.I)


def diff_spec(desc):
    """Return (difficulty, exact) for an achievement.

    `desc` is expected to be English text (the game's own string). Callers pass
    the RU description separately, because the Russian wiki translations are not
    always faithful: "Water Works" is exact OVERKILL in game but the RU page says
    "«OVERKILL» или выше", which would wrongly make it a cascading rung.
    """
    t = desc.lower()
    best = None
    for m in re.finditer(r"(?:on|at)\s+(?:the\s+)?([a-z]+(?:\s+[a-z]+)?)\s*difficulty"
                         r"|(?:на\s+уровне\s+сложности\s+)«([^»]+)»"
                         r"|(?:сложности\s+)«([^»]+)»", t):
        cand = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        cand = RU_DIFF.get(cand, cand if cand in RANK else None)
        if cand and (best is None or RANK[cand] > RANK[best]):
            best = cand
    if best is None:
        for d in DIFFS:
            if re.search(r"(?<![a-z])" + re.escape(d) + r"(?![a-z])", t) and re.search(
                    r"difficulty|сложност", t):
                if best is None or RANK[d] > RANK[best]:
                    best = d
    if best is None:
        return "easy", False
    return best, not bool(OR_ABOVE.search(t))


def diff_floor(desc):
    """Kept for callers that only need the difficulty floor."""
    return diff_spec(desc)[0]


def constraints_of(desc):
    t = desc.lower()
    out = set()
    for key, pat, _label, _ex in CONSTRAINTS:
        # patterns mix English and Russian literals; text is lower-cased first,
        # so matching must be case-insensitive or "Christmas tree" never hits
        if re.search(pat, t, re.I):
            out.add(key)
    return out


def analyse(achievements):
    """achievements: list of dicts with 'name', 'desc', 'desc_ru'."""
    items = []
    for a in achievements:
        en = a.get("desc") or ""
        ru = a.get("desc_ru") or ""
        conds = constraints_of(en + " " + ru)
        m = REPEAT.search(ru or en)
        reps = max(int(m.group(1) or m.group(2) or 1), 1) if m else 1
        # difficulty and "or above" are read from the ENGLISH string only
        floor, exact = diff_spec(en or ru)
        if floor == "easy" and ru:
            # the English string can omit the difficulty while the Russian one
            # names it ("The only one that is true" -> «Нормально»)
            rfloor, rexact = diff_spec(ru)
            if rfloor != "easy":
                floor, exact = rfloor, rexact
        items.append({
            "name": a["name"], "floor": floor, "exact": exact, "conds": conds,
            "reps": reps, "pct": a.get("pct"),
            "ladder_only": not conds and floor != "easy",
        })
    return items


EXCLUSIVE = {}
for key, _p, _l, ex in CONSTRAINTS:
    EXCLUSIVE[key] = set(ex)


def compatible(cond_set):
    for c in cond_set:
        if EXCLUSIVE.get(c, set()) & cond_set:
            return False
    return True


def plan(items):
    """Greedy set cover -> list of runs.

    A run is (difficulty, conditions) and covers an achievement when
      - the run's difficulty is at least the achievement's floor, and
      - if the achievement is exact, the run's difficulty IS that difficulty, and
      - every condition of the achievement is in the run's condition set.
    Candidate runs are built per difficulty, because an exact-difficulty
    achievement cannot be satisfied by a harder run.
    """
    if not items:
        return [], []
    allc = set()
    for i in items:
        allc |= i["conds"]

    subsets = set()
    for i in items:
        subsets.add(frozenset(i["conds"]))
    base = [frozenset(s) for s in subsets]
    for a, b in combinations(base, 2):
        subsets.add(a | b)
    if allc:
        subsets.add(frozenset(allc))
    subsets.add(frozenset())
    cond_pool = [s for s in subsets if compatible(s)]

    # difficulties worth trying: every achievement floor, every exact rung, max
    diffs = {i["floor"] for i in items}
    diffs |= {i["floor"] for i in items if i["exact"]}
    diffs.add(max((i["floor"] for i in items), key=lambda f: RANK[f]))
    pool = [(d, cs) for d in diffs for cs in cond_pool]

    def covers(run_diff, run_conds, it):
        if it["exact"]:
            if RANK[run_diff] != RANK[it["floor"]]:
                return False
        elif RANK[run_diff] < RANK[it["floor"]]:
            return False
        return it["conds"] <= run_conds

    remaining = set(range(len(items)))
    runs = []
    while remaining:
        best, best_key = None, None
        for (d, cs) in pool:
            gain = sum(1 for idx in remaining if covers(d, cs, items[idx]))
            if gain <= 0:
                continue
            # ties: prefer the easiest difficulty that still covers the same
            # achievements, then the fewest extra conditions -- a lighter plan
            # is a more realistic one to actually execute
            key = (-gain, RANK[d], len(cs))
            if best_key is None or key < best_key:
                best, best_key = (d, cs), key
        if best is None:
            break
        d, cs = best
        got = {idx for idx in remaining if covers(d, cs, items[idx])}
        runs.append({"diff": d, "conds": set(cs), "items": sorted(got)})
        remaining -= got

    # repeated achievements are grind on top of the plan
    grind = []
    for idx, it in enumerate(items):
        if it["reps"] > 1:
            grind.append({"name": it["name"], "times": it["reps"]})
    runs = refine(runs, items)
    return runs, grind


LABEL = {k: l for k, _p, l, _e in CONSTRAINTS}

# conditions that are free piggybacks: an optional objective you can tick off
# during a run you are making anyway, so they belong in the fullest run.
PIGGYBACK = {"marker", "bags_tree", "secret_object"}


def refine(runs, items):
    """Fold piggyback conditions out of thin runs into the fullest compatible one."""
    def covers(run_diff, cond_set, it):
        if it["exact"]:
            if RANK[run_diff] != RANK[it["floor"]]:
                return False
        elif RANK[run_diff] < RANK[it["floor"]]:
            return False
        return it["conds"] <= cond_set

    changed = True
    while changed and len(runs) > 1:
        changed = False
        runs.sort(key=lambda r: -len(r["items"]))
        big = runs[0]
        for r in runs[1:]:
            # a piggyback can only migrate to a run at the same difficulty, since
            # an exact-difficulty achievement would stop matching otherwise
            if r["diff"] != big["diff"]:
                continue
            for c in sorted(r["conds"] & PIGGYBACK):
                merged = big["conds"] | {c}
                if not compatible(merged):
                    continue
                got = {i for i in range(len(items)) if covers(big["diff"], merged, items[i])}
                if len(got) >= len(set(big["items"]) | set(r["items"])):
                    big["conds"] = merged
                    big["items"] = sorted(got)
                    r["items"] = [i for i in r["items"] if i not in got]
                    r["conds"] = r["conds"] - {c}
                    changed = True
            if not r["items"]:
                runs.remove(r)
                changed = True
                break
    return runs


def describe_run(run, max_floor=None):
    parts = []
    d = run.get("diff") or max_floor
    if d and d != "easy":
        parts.append("сложность " + d)
    for c in sorted(run.get("conds") or ()):
        parts.append(LABEL.get(c, c))
    return ", ".join(parts) if parts else "любая сложность"