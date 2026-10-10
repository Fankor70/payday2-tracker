# -*- coding: utf-8 -*-
"""Rebuild achievement data from the Russian wiki's per-heist linked lists.

The RU heist articles carry a "Связанные достижения" section that states which
achievements belong to that heist -- authoritative, unlike inferring it from the
English text. This stage takes the Russian name, Russian condition, heist
membership and day from there, and keeps the Steam row only for the id, the
community unlock percentage and the icon.
"""
import json, re, sys, io
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def norm(s):
    """Match key for a row name.

    "!" "?" and "*" must survive: the wiki lists «Don't Forget to Vote!»
    (Election Day, Нормально) next to «Don't Forget to Vote» (White House) as if
    they were two achievements, and the game only has the first. Stripping all
    punctuation merged the two, and the shorter White House condition then won
    and overwrote the Election Day row's Russian name, condition and heist.
    """
    s = (s or "").lower().replace("’", "'").replace("–", "-")
    s = re.sub(r"[^\w\s!?*]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


linked = json.load(open("payday/data/ru_linked.json", encoding="utf-8"))
data = json.load(open("payday/data/app_data.json", encoding="utf-8"))
A = data["achievements"]

# ---- collect the wiki's view, deduped --------------------------------------
by_en = defaultdict(dict)     # en-name -> {heist_key: {day, desc_ru, name_ru}}
heist_of_title = {}
def is_latin(s):
    """Some wiki rows carry an English name with no "(ориг. …)" suffix."""
    s = s or ""
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    return sum(1 for c in letters if ord(c) < 0x400) / len(letters) > 0.9


for key, v in linked.items():
    heist_of_title[v["title"]] = key
    for e in v["entries"]:
        if not e["name_en"]:
            if is_latin(e.get("name_ru")):
                e["name_en"] = e["name_ru"]
            else:
                continue
        n = norm(e["name_en"])
        slot = by_en[n].setdefault(key, {})
        if e.get("day") and not slot.get("day"):
            slot["day"] = e["day"]
            slot["note"] = e.get("note") or ""
        slot.setdefault("desc_ru", e["desc_ru"])
        slot.setdefault("name_ru", e["name_ru"])

# ---- apply onto the Steam rows ---------------------------------------------
NOTE_TAIL = re.compile(
    r"\s*Достижение может быть получ[её]но в\s+\d+\s*-?\s*дне контракт[аеу]?\s*"
    r"(?:«[^»]*»)?\s*\.?\s*$", re.I)

# The wiki stores editorial notes about long-gone temporary rewards inside the
# same template field as the condition ("… .С 27 января 2016 года по 2 июня 2016
# года выполнение достижения вознаграждало игрока сейфом и дрелью."). They are
# wiki history, not the requirement, and they arrived glued to the sentence
# without a space, so the card rendered as one run-on sentence.
EDITORIAL = re.compile(
    r"\s*С\s+\d{1,2}\s+\w+\s+\d{4}\s+года\s+по\s+\d{1,2}\s+\w+\s+\d{4}\s+года\s+"
    r"выполнение достижения\s+вознаграждало.*$", re.I)
# A separate note about what the drill is NOT required for, also wiki commentary.
DRILL_NOTE = re.compile(
    r"\s*Не\s+требуется\s+использование\s+дрели\..*$", re.I)


def strip_editorial(d):
    if not d:
        return d
    d = EDITORIAL.sub("", d).strip()
    d = DRILL_NOTE.sub("", d).strip()
    return d

stats = {"matched": 0, "renamed": 0, "redescribed": 0, "day": 0,
         "heists_extended": 0, "unmatched": [], "no_en_on_wiki": 0}

for a in A:
    n = norm(a["name"])
    hit = by_en.get(n)
    if not hit:
        stats["no_en_on_wiki"] += 1
        stats["unmatched"].append(a["name"])
        continue
    stats["matched"] += 1
    a["wiki_heists"] = sorted(hit.keys())
    # the wiki lists are authoritative but incomplete (Meltdown shows 10 of 15),
    # so keep the attribution derived from the game's own English strings too
    merged = sorted(set(a.get("heists") or []) | set(a["wiki_heists"]))
    if merged != sorted(a.get("heists") or []):
        stats["heists_extended"] += 1
    a["heists"] = merged
    days = sorted({v["day"] for v in hit.values() if v.get("day")})
    if days:
        a["day"] = days[0]
        a["days"] = days
        stats["day"] += 1
    # prefer the shortest description: some pages append a stray second sentence
    best = min(hit.values(), key=lambda v: len(v.get("desc_ru") or "zzz"))
    d = best.get("desc_ru") or ""
    note = best.get("note") or ""
    if note and note in d:
        d = NOTE_TAIL.sub("", d).strip()
    d = strip_editorial(d)
    # a missing space after a full stop is how the wiki glued these on; leave
    # real sentences alone but do not render two sentences as one word
    d = re.sub(r"(?<=[.!?])(?=[А-ЯA-Z])", " ", d).strip()
    if d:
        a["desc_ru"] = d
        stats["redescribed"] += 1
    if best.get("name_ru"):
        a["name_ru"] = best["name_ru"]
        stats["renamed"] += 1

# ---- hand-written names win over a wiki that has none ---------------------
# translate.py runs BEFORE this stage, so a row whose wiki entry leaves the name
# in English ("Jack the Rippers, Prison Slippers!") would overwrite the manual
# translation applied moments earlier. Re-apply it where the wiki gave no
# Russian of its own, so the audit table stays the last word on wording.
from trans_names import NAMES as _NAMES          # noqa: E402

restored = 0
for a in A:
    if re.search(r"[А-Яа-яЁё]", a.get("name_ru") or ""):
        continue                                 # the wiki really did translate it
    entry = _NAMES.get(a["name"])
    if entry and entry[0]:
        a["name_ru"] = entry[0]
        restored += 1

json.dump(data, open("payday/data/app_data.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("достижений всего:", len(A))
print("сопоставлено со списками вики:", stats["matched"])
print("  из них переименовано:", stats["renamed"])
print("  из них с русским условием:", stats["redescribed"])
print("  с указанием дня:", stats["day"])
print("  привязку к хайстам расширила вики:", stats["heists_extended"])
print("осталось без списка на вики:", stats["no_en_on_wiki"])
for nm in stats["unmatched"][:25]:
    print("   -", nm)

# how many heists does the wiki itself cover
covered = set()
for v in linked.values():
    covered.add(v["title"])
print("\nхостов, описанных на вики со списком:", len(covered))