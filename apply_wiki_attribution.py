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

# ------------------------------------------------ EN referee: cross-listings
# The RU wiki spreads some pack achievements over every heist where they can
# technically be done ("Pink Slip", enter a drivable vehicle, sat on SEVEN
# heists including car-less ones). The EN wiki -- the canonical per-heist
# lists -- contradicts that. A membership survives only when the row's own
# text names this heist, the EN wiki lists it on this heist's page, or this
# heist is the row's ONLY wiki claim.
def _same_heist(k, h):
    """Does the text-named key K refer to heist H? Folded parents and aliased
    keys spell differently from the page ("Border Crossing" vs "Border
    Crossing Heists"), and the folded parent's name is already the Russian
    one -- so compare against BOTH the name and the page."""
    nm = norm(HEISTS.get(k, (k.replace("_", " "), []))[0])
    if not nm:
        return False
    for src in (h.get("name"), h.get("page")):
        hn = norm(src)
        if hn and (nm in hn or hn in nm):
            return True
    return False

en_mem = json.load(open("payday/data/en_wiki_membership.json", encoding="utf-8"))
en_by_key = {key_for(p): set(norm(n) for n in names) for p, names in en_mem.items()}
PACK_ADDITIONAL = {"Pink Slip": "Car Shop"}   # EN wiki: The Butcher's BBQ Pack → Additional

stripped = {}                                 # heist page -> ids removed
for h in data["heists"]:
    hk = h["_key"]
    en = en_by_key.get(hk, set())
    kept, out = [], []
    for i in h["ids"]:
        a = by_id[i]
        nmrow = norm(a["name"])
        nk = _named_heists(a)
        if hk in nk or any(_same_heist(k, h) for k in nk):
            kept.append(i)
            continue
        if nmrow in en:
            kept.append(i)
            continue
        ru_keys = {key_for(w) for w in (a.get("wiki_heists") or [])}
        if hk in ru_keys and len(ru_keys) == 1:
            kept.append(i)                    # the only wiki claim: trust it
            continue
        out.append(i)
    if out:
        h["ids"] = kept
        for v in (h.get("variants") or []):
            v["ids"] = sorted(set(v["ids"]) - set(out))
        stripped[h["page"]] = out
        print("  EN-арбитр: снято с %-26s %d: %s" %
              (h["name"][:26], len(out), ", ".join(by_id[i]["name"][:18] for i in out[:4])))

# pack achievements the EN wiki keeps under a DLC pack go to that pack's heist
for nm, page in PACK_ADDITIONAL.items():
    ids = [i for pg, ids in stripped.items() for i in ids if by_id[i]["name"] == nm]
    host = next((h for h in data["heists"] if h["page"] == page), None)
    if ids and host:
        host["ids"] = sorted(set(host["ids"]) | set(ids))
        for i in ids:
            by_id[i]["fit"] = "extra"
            for h2 in data["heists"]:
                if h2 is not host and i in h2["ids"]:
                    h2["ids"].remove(i)
        for p in list(stripped):
            if any(by_id[i]["name"] == nm for i in stripped[p]):
                del stripped[p]
        # the row sat in the global bucket and parallel lists since build_v3 saw
        # no heist for it -- leaving it there would show it on two screens
        data["global_ids"] = [g for g in (data.get("global_ids") or []) if g not in ids]
        par = data.get("parallel") or {}
        for bk in par:
            par[bk] = [i for i in par[bk] if i not in ids]
        print("  EN-арбитр: %r -> %s (pack additional)" % (nm, page))

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