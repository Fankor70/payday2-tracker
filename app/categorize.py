# -*- coding: utf-8 -*-
"""Split every achievement into the categories that matter for planning a run.

The old split was descriptive (what kind of achievement is this). The useful one
for a route is "what does it cost me":

  ladder    - falls out of simply finishing on a difficulty (the free ones)
  run_cond  - costs something DURING the run (no alarm, one bag, speed, stealth)
  objective - costs a specific action in the heist (find, kill, collect, place)
  loadout   - costs equipment: a specific mask, outfit or weapon on you
  crew      - costs other players
  farmable  - account-wide counters you advance in any run (kills, repeats)
  meta      - account progression that needs no run at all (levels, infamy)

The last two are the point of the whole exercise: they do not need their own
heist, so every run is a chance to advance them and the route says so.
"""
import json, re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PAY = os.path.dirname(HERE)
TARGET = (sys.argv[1] if len(sys.argv) > 1
          else os.path.join(PAY, "data", "app_final.json"))

CATEGORIES = [
    ("ladder",   "Лестница сложности",   "Добирается просто прохождением"),
    ("run_cond", "Условия захода",      "Нужно соблюсти во время захода"),
    ("objective","Объекты миссии",      "Найти, собрать, сделать на карте"),
    ("loadout",  "Маски и снаряжение",   "Надеть или взять в руки"),
    ("crew",     "Нужен полный состав",  "Четыре игрока"),
    ("farmable", "Общие счётчики",      "Капают в любом заходе"),
    ("meta",     "Прогресс аккаунта",   "Без захода: уровни, инфомити"),
]

RUN_COND = re.compile(
    r"without (?:triggering|sounding|setting off|raising|having)[^.,]{0,25}alarm|"
    r"without (?:killing|shooting|dying|being)|no alarm|"
    r"without (?:taking damage|being hit|being shot)|untouched|untarnished|"
    r"in stealth|while in stealth|without being seen|"
    r"within \d+ ?min|under \d+ ?min|in under \d+ seconds|"
    r"carry(?:ing)? only|only (?:one|a single) bag|one bag|"
    r"не поднима(?:я|й) тревог|без тревоги|по тихому|скрытн|"
    r"не уби(?:в|ивая)|не стреля|за \d+ минут|не получив урона|только одну сумк|"
    r"не (?:быть|дай) убит|не потерять|"
    r"without (?:using|any|your|a|the) [a-z ]*?(?:weapon|gun|skills|tools)|"
    r"using no skills|only (?:the )?(?:interactor|zip|skyhook|sewer)|"
    r"without (?:using|breaking|opening) |through the sewers?|with the skyhook|"
    r"не (?:использу|польз|стреля|взлом)|только (?:невесомый|интерактор|молот)|"
    r"через (?:канализац|небесн)", re.I)

OBJECTIVE = re.compile(
    r"\b(?:find|locate|discover|collect|place|put|bring|secure|obtain|get|reach|"
    r"escort|open|cut|throw|plant|carry|tag|press|answer|trade|deliver|hide|"
    r"найди|обнаруж|собери|положи|принеси|вынеси|достань|"
    r"эвакуируй|сопроводи|открой|перереж|брось|установи|доставь|спрячь|"
    r"ответь|обменяй|отметь|нажми)\b", re.I)

LOADOUT = re.compile(
    # no bare "with the": that matched "with the One Down mechanic" and filed
    # every Death Sentence + One Down rung under equipment instead of the ladder
    r"\b(?:wearing|equipped|loadout|wielding|armed)\b|"
    r"\b(?:mask|outfit|armou?r)s?\b|"
    r"\busing (?:only |just |a |an |the )?[a-z0-9' ]{0,30}?"
    r"(?:weapon|gun|rifle|shotgun|pistol|smg|sniper|lmg|blade|bat|saw)\b|"
    r"наде(?:в|те|ва)|нося|вооруже[нн]|"
    r"костюм[аеуы]?|маск[ауеы]|брон[яею]|"
    r"с (?:оружием|пистолетом|дробовиком|автоматом|винтовкой)|"
    r"используя (?:только |пистолет|дробовик|автомат|винтовк)", re.I)

FARMABLE = re.compile(
    r"\bkill \d|\bkill\b|\bkills\b|\d+ (?:kills|enemies|civilians|guards|hostages|clones|"
    r"dozers|bulldozers)|"
    r"\d+ (?:times|reps)|once (?:more|again)|headshot kills?|"
    r"уби(?:ть|й|ва|ть) \d|\d+ (?:раз|убийств)|"
    r"сбить \d|\d+ (?:голов|kill)", re.I)

META = re.compile(
    r"\breach (?:reputation )?level|reputation level \d|reach infamy|"
    r"own \d+ (?:weapons|outfits|masks)|"
    r"spend \$|total cash|total spendable|buy |modify a weapon|modify a mask|"
    r"equip an armor|collect \d+ (?:package|postcard|relic)|"
    r"достигни уровн|уровн[яи] репутации|инфомити|"
    r"потра[тьт] \$|модифицируй|над[её]н|"
    r"купи|собери \d+ (?:посыл|открыт|коллекц)", re.I)


REWARD_TAIL = re.compile(r"\s*(?:Unlocks?|Unlocking)\b.*$", re.I)
REWARD_TAIL_RU = re.compile(r"\s*(?:Выполнение достижения открывает|Открывает)\b.*$", re.I)


def condition_only(en, ru):
    """The CONDITION, without the "Unlocks the ..." reward sentence.

    Rewards name masks and outfits constantly, and letting that text into the
    classifier filed plain difficulty rungs under equipment.
    """
    e = REWARD_TAIL.sub("", en or "")
    r = REWARD_TAIL_RU.sub("", ru or "")
    return e, r


def classify(a):
    en, ru = condition_only(a.get("desc") or "", a.get("desc_ru") or "")
    t = en + " " + ru
    has_heist = bool(a.get("heists"))

    # a full lobby is a cost of its own and outranks the rest
    if a.get("crew4"):
        return "crew"

    # No heist means no run is attached. Then the only question is whether any
    # run at all advances it (a counter) or whether it is pure account progress.
    if not has_heist:
        if FARMABLE.search(t) and not META.search(t):
            return "farmable"
        return "meta"

    # tied to a heist from here on
    if RUN_COND.search(t):
        return "run_cond"
    if LOADOUT.search(t):
        return "loadout"
    if OBJECTIVE.search(t):
        return "objective"
    if a.get("category") == "difficulty_ladder" or a.get("difficulties"):
        return "ladder"
    return "objective"


data = json.load(open(TARGET, encoding="utf-8"))
A = data["achievements"]

changed = 0
for a in A:
    c = classify(a)
    if a.get("plan_cat") != c:
        changed += 1
    a["plan_cat"] = c

json.dump(data, open(TARGET, "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"))

from collections import Counter
cnt = Counter(a["plan_cat"] for a in A)
print("категории для планирования:")
for key, ru, hint in CATEGORIES:
    print(f"   {cnt.get(key,0):5d}  {ru:24s} — {hint}")
print()
print("всего:", len(A), "| переразмечено:", changed)
for key, ru, _h in CATEGORIES:
    ex = [a["name"] for a in A if a.get("plan_cat") == key][:3]
    print(f"  {ru}: {ex}")