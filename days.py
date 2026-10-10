# -*- coding: utf-8 -*-
"""Split multi-day heists into per-day achievement lists.

A multi-day heist is ONE contract with several days, and the game names the day
in the achievement text: "On day 2 of Rats", "на 2 день контракта «Крысы»".
Without this split a day-specific achievement sits in the same list as ones you
can pick up on any run.
"""
import re
from collections import defaultdict

DAY_EN = re.compile(
    r"\b(?:on|in|complete|finish)\s+(?:the\s+)?(?:first\s+|second\s+|third\s+)?day\s*(\d)\s+of\s+"
    r"(?:the\s+)?([^,.\n]{2,40}?)(?:\s+job|\s+heist)?[,.]", re.I)
DAY_RU = re.compile(r"(?:в\s+|на\s+)?(\d)\s*-?\s*(?:день|дн\.)[^,.\n]{0,20}?«([^»]{2,40})»")

DAY_WORDS = {1: "Первый", 2: "Второй", 3: "Третий", 4: "Четвёртый", 5: "Пятый"}

# the game string does not always match the registry page name
DAY_JOB_FIX = {
    "rats job or the cook off": "rats",
    "cook off": "rats",
    "biker": "the biker",
    "the biker heist": "the biker",
    "prison nightmare": "hoxton breakout",
    "hoxton break out": "hoxton breakout",
    "big  bank": "big bank",
}


def _match_page(job, pages, ach):
    """Find the registry heist this job string names.

    Exactness matters: the game says "On day 1 of the Rats job", but "rats" is also
    a substring of "Lab Rats", so a naive substring scan files Rats' day-1 rung
    under Lab Rats. Try exact names first, then prefer the SHORTEST page that
    contains the string.
    """
    def norm(x):
        return re.sub(r"[^a-z0-9]+", "", (x or "").lower())

    key = norm(job)
    # 1. exact page name / internal job name
    for page, h in pages.items():
        if norm(page) == key or norm(h.get("job") or "") == key:
            return page
    # 2. substring, shortest page name wins (so "rats" beats "lab rats")
    hits = [(len(page), page) for page, h in pages.items()
            if key and key in norm(page + (h.get("job") or ""))]
    if hits:
        return sorted(hits)[0][1]
    # 3. fuzzy word overlap
    words = [w for w in re.split(r"\W+", job) if len(w) > 3]
    best, best_score = None, 0
    for page, h in pages.items():
        blob = re.sub(r"[^a-z0-9]+", " ", (page + " " + (h.get("job") or "")).lower())
        score = sum(1 for w in words if w in blob)
        if score > best_score:
            best, best_score = page, score
    return best if best_score >= max(1, len(words) - 1) else None


def detect_days(all_ids, pages, ach):
    """-> {page: {day_number: [ids]}} straight from the achievement texts."""
    found = defaultdict(lambda: defaultdict(set))
    for i in all_ids:
        a = ach[i]
        text = (a["desc"] or "") + " " + (a.get("desc_ru") or "")
        hits = [(int(m.group(1)), m.group(2).strip().lower()) for m in DAY_EN.finditer(text)]
        hits += [(int(d), job.strip().lower()) for d, job in DAY_RU.findall(text)]
        for num, job in hits:
            job = DAY_JOB_FIX.get(job, job)
            page = _match_page(job, pages, ach)
            if page:
                found[page][num].add(i)
    return {p: {d: sorted(v) for d, v in sorted(days.items()) if v}
            for p, days in found.items()}


def make_day_variants(pages, ach, log=print):
    """One heist, several days -> a variant entry per day."""
    all_ids = sorted({i for h in pages.values() for i in h["ids"]})
    made = {}
    for page, days in detect_days(all_ids, pages, ach).items():
        host = pages.get(page)
        if not host or len(days) < 2:
            continue
        day_ids = sorted(set().union(*days.values()))
        shared = [i for i in host["ids"] if i not in set(day_ids)]
        variants = [{
            "ru": f"{DAY_WORDS.get(d, 'День')} день",
            "en": f"Day {d}",
            "day": d,
            "own": len(ids),
            "ids": sorted(ids),
            "shared": sorted(shared),
        } for d, ids in days.items()]
        made[page] = {
            "kind": "day",
            "variants": variants,
            "shared": sorted(shared),
            "all_ids": sorted(set(host["ids"])),
        }
        log(f"{page:26s} дней {len(variants)}: " +
            ", ".join(f"{v['en']}={v['own']}" for v in variants) +
            f" | общих {len(shared)}")
    return made