# -*- coding: utf-8 -*-
"""Pick a representative showcase of achievements to eyeball for correctness."""
import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "payday")
from heuristics import HEISTS

recs = json.load(open("payday/data/ach_final.json", encoding="utf-8"))
by = {r["name"]: r for r in recs}

WANT = [
    # name, why it is interesting for verification
    "Honor Among Thieves",     # 4-player crew loadout, DLC-gated
    "Cat Burglar",             # no-alarm, mask+material+pattern reward
    "Culture Vultures",        # extra-bags threshold, mask reward
    "Smoke and Mirrors",       # speed run
    "Diamonds in the Rough",   # alarm triggered, puzzle, difficulty
    "Precious Stones",         # plain difficulty ladder rung
    "Bad Code",                # Death Sentence + One Down
    "Criminal Origins",        # contractor-wide cumulative (all contracts)
    "Goat Herder",             # single-heist cumulative
    "Slasher",                 # kill-count cumulative
    "Firm Hand",               # weapon-specific
    "Closer",                  # close-range / blind
    "The Cleaner",             # kill-count
    "Fully Loaded",            # global collection cumulative
    "Weapon Collector",        # global collection cumulative
    "Cash Bug",                # global money
    "Beneath the Surface",     # ---
    "Where's My Briefcase?",   # ---
    "The Mole",                # ---
    "Boom!",                   # ---
]


def fmt(r):
    if not r:
        return "  !! NOT FOUND"
    lines = []
    lines.append("  name:      %s" % r["name"])
    lines.append("  cond:      %s" % r["desc"])
    lines.append("  heist(s):  %s" % (", ".join(HEISTS.get(h, (h,))[0] for h in r["heists"]) or "(общее / не привязано)"))
    lines.append("  difficulty:%s" % (", ".join(r["difficulties"]) or "-"))
    rw = r.get("rewards") or {}
    if rw:
        parts = []
        for k, v in rw.items():
            parts.append("%s: %s" % (k, "; ".join(v)))
        lines.append("  reward:    %s" % " | ".join(parts))
    lines.append("  tags:      %s" % ", ".join(r["tags"]))
    lines.append("  wiki src:  %s" % r["source"])
    return "\n".join(lines)


for i in range(0, len(WANT), 1):
    n = WANT[i]
    print("=" * 78)
    print("%d. %s" % (i + 1, n))
    print(fmt(by.get(n)))

print()
print("=" * 78)
print("ЧТО ВЫШЛО В ДАННЫХ")
print("всего достижений:", len(recs))
print("привязано к хайсту:", sum(1 for r in recs if r["heists"]))
print("с указанной сложностью:", sum(1 for r in recs if r["difficulties"]))
print("с наградой:", sum(1 for r in recs if r["has_reward"]))
print("условие на 4 игроков:", sum(1 for r in recs if "four_crew" in r["tags"]))
print("без тревоги:", sum(1 for r in recs if "no_alarm" in r["tags"]))
print("тайминг:", sum(1 for r in recs if "speed_run" in r["tags"]))
print("счётчик убийств:", sum(1 for r in recs if "kill_count" in r["tags"]))