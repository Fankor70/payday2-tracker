# -*- coding: utf-8 -*-
"""Pull a numeric target out of every achievement description.

"Kill 378 enemies", "Collect 15 packages", "place 61 doctor bags" all carry the
number the player is grinding towards. Extracting it is what lets the app show a
0 -> N counter instead of a yes/no checkbox.
"""
import json, re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PAY = os.path.dirname(HERE)
TARGET = (sys.argv[1] if len(sys.argv) > 1
          else os.path.join(PAY, "data", "app_final.json"))

# "kill 100 cops", "убить 378 противников", "collect 15 packages"
KILL = re.compile(
    r"\b(?:kill|уби(?:ть|й|ва|в|й|те))\s*(?:at least\s+|не менее\s+)?(\d+)", re.I)
# "collect 15 packages", "gather 5", "собери 15 посылок"
COLLECT = re.compile(
    r"\b(?:collect|gather|accumulate|собери(?:те)?)\s*(?:at least\s+)?(\d+)", re.I)
# "place 61 doctor bags", "put 4 body bags", "вынесите 16 сумок"
PLACE = re.compile(
    r"\b(?:place|put|secure|steal|вынесите?|разместите?)\s*(?:at least\s+)?(\d+)", re.I)
# bare: "16 secured bags", "61 doctor bags", "7 bags worth of meth"
BARE = re.compile(
    r"(\d+)\s+(?:secured\s+)?(?:doctor\s+|body\s+|money\s+)?(?:bags?|packages?|"
    r"enemies|кг|сумок|посылок|врагов|убийств)", re.I)


def target_of(a):
    en = a.get("desc") or ""
    ru = a.get("desc_ru") or ""
    for rx in (KILL, COLLECT, PLACE, BARE):
        m = rx.search(en) or rx.search(ru)
        if m:
            n = int(m.group(1))
            if 1 < n <= 100000:
                return n
    # "find the trophy five times" -> spelled-out numbers
    WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "twenty": 20, "thirty": 30}
    m = re.search(r"\b(two|three|four|five|six|seven|eight|nine|ten|twenty|thirty)\s+times",
                   en, re.I)
    if m:
        return WORDS[m.group(1).lower()]
    return None


data = json.load(open(TARGET, encoding="utf-8"))
n = 0
for a in data["achievements"]:
    t = target_of(a)
    if t:
        a["target"] = t
        n += 1

json.dump(data, open(TARGET, "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"))

done = set(data.get("done") or [])
left = [a for a in data["achievements"] if a.get("target") and a["id"] not in done]
print("с числовой целью:", n, "из", len(data["achievements"]))
print("из них ещё не закрыто:", len(left))
print("крупнейшие цели:", sorted((a["target"], a["name"]) for a in data["achievements"]
                                 if a.get("target"))[-6:])