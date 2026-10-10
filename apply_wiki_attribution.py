# -*- coding: utf-8 -*-
"""Rebuild heist membership from the wiki so the tracker is 1:1 with it.

The heuristics read the English condition text and are good but not exact; the
wiki states membership outright. So: take the wiki as the source of truth for
which achievements sit on which heist page, keep the heuristics only for
achievements the wiki lists nowhere, and record the difference.
"""
import json, re, sys, io, difflib
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from heist_aliases import key_for, norm
from heuristics import HEISTS


def _named_heists(a):
    """Heist keys the row's own condition names (quotes stripped: a
    "Diamond Heist" mask is an item, not the contract)."""
    t = re.sub(r'"[^"]*"', " ", (a.get("desc") or "").lower())
    named = set()
    for key, (nm, aliases) in HEISTS.items():
        if any(re.search(r"(?<![a-z])" + re.escape(x.lower()) + r"(?![a-z])", t)
               for x in [nm] + list(aliases)):
            named.add(key)
    return named


def rescue_ok(a, hkey):
    """The fuzzy rescue fixes wiki typos; it must not attach a row to a heist
    its own text contradicts. "Every Dog Has His Day" names the Scarface
    Mansion job -- a wiki row spelling it "Its Day" on the Watchdogs page is
    a wiki error, not a second membership. Rows naming no heist at all
    (flavour-text hidden ones) carry no contradiction and stay allowed."""
    named = _named_heists(a)
    return hkey in named or not named



def text_supports(a, hkey):
    """True when the row's own condition names this heist."""
    nm, aliases = HEISTS.get(hkey, (hkey.replace("_", " "), []))
    t = re.sub(r'"[^"]*"', " ", (a.get("desc") or "").lower())
    return any(re.search(r"(?<![a-z])" + re.escape(x.lower()) + r"(?![a-z])", t)
               for x in [nm] + list(aliases))

data = json.load(open("payday/data/app_final.json", encoding="utf-8"))
A = data["achievements"]
by_id = {a["id"]: a for a in A}

# ------------------------------------------------ what the wiki assigns, by key
wiki_ids = defaultdict(set)          # heist key -> achievement ids
for a in A:
    for wh in (a.get("wiki_heists") or []):
        wiki_ids[key_for(wh)].add(a["id"])

# ------------------------------------------------ fuzzy rescue: wiki typos
by_name = {norm(a["name"]): a["id"] for a in A}
resolved_typos = 0
for key, v in list(json.load(open("payday/data/ru_linked.json",
                                  encoding="utf-8")).items()):
    k = key_for(key)
    for e in v["entries"]:
        if not e.get("name_en"):
            continue
        n = norm(e["name_en"])
        if n in by_name:
            if rescue_ok(by_id[by_name[n]], k):
                wiki_ids[k].add(by_name[n])
            continue
        near = difflib.get_close_matches(n, list(by_name), n=1, cutoff=0.9)
        if near:
            aid = by_name[near[0]]
            if rescue_ok(by_id[aid], k):
                wiki_ids[k].add(aid)
                resolved_typos += 1

# ------------------------------------------------ apply
moved, kept_only_heuristic = 0, 0
page_key = {}
for h in data["heists"]:
    page_key[h["page"]] = key_for(h["page"])
    page_key[h["name"]] = key_for(h["name"])
    h["_key"] = key_for(h["page"])

heist_of = {h["page"]: set() for h in data["heists"]}

# the heist's own wiki key
for h in data["heists"]:
    heist_of[h["page"]] |= wiki_ids.get(h["_key"], set())
    h["_key2"] = key_for(h["name"])

# a variant's achievements belong to the parent page as well
for h in data["heists"]:
    for v in (h.get("variants") or []):
        hk = key_for(v.get("en") or v.get("ru") or "")
        heist_of[h["page"]] |= wiki_ids.get(hk, set())

before = {}
for h in data["heists"]:
    before[h["page"]] = set(h["ids"])

for h in data["heists"]:
    old = set(h["ids"])
    # The wiki is authoritative about what it lists, but several per-heist tables
    # are incomplete. Replacing the list wholesale dropped rows the wiki merely
    # omits and exiled them to the global bucket, so ADD to what we already had.
    wiki_side = set(heist_of.get(h["page"], set()))
    if not wiki_side:
        kept_only_heuristic += 1
    # ...but an id that only CAME from the build stage must be re-checked. Four
    # sibling pairs inherited each other's whole pools ("Lab Rats" contains
    # "Rats", the Aftershock/Prison Nightmare aliases, Armored Transport
    # dumping the Train rows on the five city maps), which left both heists of
    # a pair with identical lists. An inherited id stays only when the wiki
    # lists it on THIS page or the row's own text names this heist. Pages
    # without a key of their own (the "Бомба" parent of two variants) are
    # skipped -- their pools are the union of their variants by design.
    if h["_key"] in HEISTS:
        kept_old = set()
        for i in old:
            a = by_id[i]
            wkeys = {key_for(w) for w in (a.get("wiki_heists") or [])}
            if h["_key"] in wkeys or text_supports(a, h["_key"]):
                kept_old.add(i)
    else:
        kept_old = old
    h["ids"] = sorted(kept_old | wiki_side)
    new = set(h["ids"])
    # re-split variants from the new membership where possible
    for v in (h.get("variants") or []):
        v["ids"] = sorted(set(v["ids"]) & new) or sorted(new)
    if old != new:
        moved += 1

# anything the rebuild left on no heist must still be reachable, so it falls
# back into the global bucket rather than vanishing from the app
placed = set()
for h in data["heists"]:
    placed |= set(h["ids"])
    for v in (h.get("variants") or []):
        placed |= set(v["ids"])
glob = set(data.get("global_ids") or [])
orphan = sorted(set(by_id) - placed - glob)
if orphan:
    data["global_ids"] = sorted(glob | set(orphan))

json.dump(data, open("payday/data/app_final.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("страниц перестроено по вики:", moved)
print("хостов без списка на вики (оставлены эвристикой):", kept_only_heuristic)
print("опечаток вики сопоставлено по близости:", resolved_typos)
print()
tot = sum(len(h["ids"]) for h in data["heists"])
print("в глобальные отправлено после пересборки:", len(orphan))
print("всего привязок хайст<->достижение:", tot)