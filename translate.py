# -*- coding: utf-8 -*-
"""Translate the achievement rows the Russian wiki never covered.

Most are formulaic ("Complete the X job on the Y difficulty or above"), so those
are produced from a template using the Russian heist and difficulty names we
already have. The genuinely one-off joke rows are filled in from TRANSLATIONS.
"""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DIFF_RU = {
    "easy": "Легко", "normal": "Нормально", "hard": "Сложно",
    "very hard": "Очень сложно", "overkill": "OVERKILL", "mayhem": "Хаос",
    "death wish": "Жажда смерти", "below zero": "Ниже нуля",
    "death sentence": "Смертный приговор",
}
DIFF_RU_UP = {"death wish": "Жажда смерти", "death sentence": "Смертный приговор"}

data = json.load(open("payday/data/app_data.json", encoding="utf-8"))
A = data["achievements"]

# ---- Russian name for every English job string we can meet -----------------
# read the Russian heist articles directly: this runs BEFORE build_v3 attaches
# name_ru to the heist list, so the registry cannot be the source here
JOB_RU = {}
try:
    for v in json.load(open("payday/data/ru_heists.json", encoding="utf-8")).values():
        ru, en = v.get("name_ru"), v.get("name_en")
        if not ru or not en:
            continue
        JOB_RU.setdefault(en.strip().lower(), ru)
        JOB_RU.setdefault((v.get("title") or "").strip().lower(), ru)
except Exception as exc:  # noqa: BLE001 - the registry below is the fallback
    print("ru_heists.json недоступен:", exc)

for h in data.get("heists", []):
    en, ru = h.get("name"), h.get("name_ru")
    if en and ru:
        JOB_RU.setdefault(en.strip().lower(), ru)
        JOB_RU.setdefault(h["page"].strip().lower(), ru)
    for v in (h.get("variants") or []):
        base = (v.get("en") or "").strip()
        if not base:
            continue
        if ":" in base:
            head, _tail = base.split(":", 1)
            hr = JOB_RU.get(head.strip().lower())
            if hr:
                JOB_RU.setdefault(base.lower(), f"{hr} ({v['ru']})")
        else:
            JOB_RU.setdefault(base.lower(), v["ru"])

CONTRACTOR_RU = {
    "bain": "Бейна", "vlad": "Влада", "locke": "Лока", "hector": "Гектора",
    "jimmy": "Джимми", "the butcher": "Мясника", "the elephant": "Слона",
    "the continental": "Континенталь", "the dentist": "Дантиста",
    "charon": "Харона", "jiu feng": "Цзю Фэна",
}

FALLBACK = {
    "boat load": "Погрузка на судно", "heat street": "Улица схватки",
    "the diamond": "Бриллиант", "big bank": "Большой банк",
    "mallcrasher": "Крушитель", "golden grin casino": "Казино Golden Grin",
    "san martín bank": "Банк San Martín", "first world bank": "Первый Всемирный Банк",
    "diamond heist": "Кража бриллиантов", "prison nightmare": "Тюремный кошмар",
    "the alesso heist": "Алессо", "slaughterhouse": "Скотобойня",
    "black cat": "Black Cat", "ukrainian prisoner": "Украинский заключенный",
    "heists in the city of gold": "всех ограблений кампании «Город золота»",
    # the six the Russian wiki never translated
    "crude awakening": "Грязное пробуждение",
    "hostile takeover": "Враждебный перехват",
    "lost in transit": "Потерянный груз",
    "midland ranch": "Ранч в Мидленде",
    "mountain master": "Хозяин горы",
    "under the hammer": "Под молотом",
    # maps the game names in achievement text but which are not registry pages
    "boat load": "Погрузка на судно", "goat simulator": "Симулятор козы",
    "birth of sky": "Рождение небес", "beneath the mountain": "У подножия горы",
    "murky station": "Станция Murkywater", "boiling point": "Точка кипения",
    "brooklyn 10-10": "Бруклин 10-10", "yacht": "Яхта",
    "breakin' feds": "Проникновение к федералам",
    "buluc's mansion": "Особняк Булука", "dragon heist": "Кража дракона",
    "shacklethorne auction": "Аукцион Шаклторн",
    "sleeping customers": "Спящие клиенты", "framing frame": "Подстава с картинами",
    "transport: park": "Транспорт: Парк", "transport: downtown": "Транспорт: Центр города",
    "transport: underpass": "Транспорт: Проезд", "transport: crossroads": "Транспорт: Перекресток",
    "transport: harbor": "Транспорт: Гавань", "transport: train heist": "Ограбление поезда",
    "first world bank": "Первый Всемирный Банк",
}


def job_ru(job):
    k = job.strip().lower().rstrip(".")
    lead = re.sub(r"^the\s+", "", k)          # only a LEADING "the"
    cands = [k, lead, "the " + lead, lead.replace(" heist", "").strip()]
    # "Transport: Crossroads" style: try each side of the colon too
    if ":" in k:
        head, tail = k.split(":", 1)
        cands += [head.strip(), tail.strip()]
    for cand in cands:
        cand = (cand or "").strip()
        if not cand:
            continue
        if cand in JOB_RU:
            return JOB_RU[cand]
        if cand in FALLBACK:
            return FALLBACK[cand]
    return None


def diff_ru(d):
    return DIFF_RU.get(d.strip().lower(), d)


TEMPLATES = [
    # Complete the X job on the Y difficulty or above.
    (re.compile(r"^Complete (.+?) job on (?:the )?([a-z ]+?) difficulty or above\.$", re.I),
     lambda m: f"Завершите контракт «{job_ru(m.group(1))}» на уровне сложности "
               f"«{diff_ru(m.group(2))}» или выше."),
    # ... with the One Down mechanic activated.
    (re.compile(r"^Complete (.+?) job on (?:the )?([a-z ]+?) difficulty with the One Down mechanic activated\.$", re.I),
     lambda m: f"Завершите контракт «{job_ru(m.group(1))}» на уровне сложности "
               f"«{diff_ru(m.group(2))}» с включённым модификатором одного падения."),
    (re.compile(r"^Complete (.+?) job on (?:the )?([a-z ]+?) difficulty with One Down activated\.$", re.I),
     lambda m: f"Завершите контракт «{job_ru(m.group(1))}» на уровне сложности "
               f"«{diff_ru(m.group(2))}» с включённым модификатором одного падения."),
    # Holdout waves
    (re.compile(r"^Having started from wave 1, beat wave (\d+) of Holdout on (?:the )?(.+?) heist\.?$", re.I),
     lambda m: f"Начав с волны 1, пройдите волну {m.group(1)} режима «Засада» "
               f"в ограблении «{job_ru(m.group(2))}»."),
    (re.compile(r"^Having started from wave 1, beat wave (\d+) of Holdout on (?:the )?(.+?)\.$", re.I),
     lambda m: f"Начав с волны 1, пройдите волну {m.group(1)} режима «Засада» "
               f"в ограблении «{job_ru(m.group(2))}»."),
    # all contracts of a contractor
    (re.compile(r"^Complete all of (?:the )?([A-Za-z' ]+?)'s contracts on (?:the )?([a-z ]+?) difficulty or above\.$", re.I),
     lambda m: f"Завершите все контракты {CONTRACTOR_RU.get(m.group(1).strip().lower(), m.group(1))} "
               f"на уровне сложности «{diff_ru(m.group(2))}» или выше."),
    # In the X job, ... -> Завершая контракт «X», ...
    (re.compile(r"^In (?:the )?(.+?) job, (.+)$", re.I),
     lambda m: (f"Завершая контракт «{job_ru(m.group(1))}», "
                + tail_ru(m.group(2).strip()))),
    (re.compile(r"^On (?:the )?(.+?) job, (.+)$", re.I),
     lambda m: f"В контракте «{job_ru(m.group(1))}» " + tail_ru(m.group(2).strip())),
    (re.compile(r"^Complete (.+?) job, (.+)$", re.I),
     lambda m: f"Завершите контракт «{job_ru(m.group(1))}», " + tail_ru(m.group(2).strip())),
]

TAIL = [
    (re.compile(r"complete the heist (.+)$", re.I), r"пройдите ограбление \1"),
    (re.compile(r"find and (.+)$", re.I), r"найдите и \1"),
    (re.compile(r"find (.+)$", re.I), r"найдите \1"),
    (re.compile(r"kill (\d+|\w+) (.+)$", re.I), r"убивайте \1 \2"),
    (re.compile(r"get (\d+) (.+)$", re.I), r"получите \1 \2"),
    (re.compile(r"secure (.+)$", re.I), r"вынесите \1"),
    (re.compile(r"destroy (.+)$", re.I), r"уничтожьте \1"),
    (re.compile(r"use (.+)$", re.I), r"используйте \1"),
    (re.compile(r"throw (.+)$", re.I), r"бросьте \1"),
    (re.compile(r"reach (.+)$", re.I), r"достигните \1"),
]


def tail_ru(s):
    for pat, rep in TAIL:
        if pat.match(s):
            return pat.sub(rep, s)
    return s


# ---- one-off rows the templates cannot reach --------------------------------
from trans_names import NAMES, DESCS


def _key(s):
    """Curly and straight apostrophes must not create two spellings of a name."""
    return (s or "").replace("’", "'").strip()


def apply():
    names_done = descs_done = 0
    unresolved = []
    for a in A:
        k = _key(a["name"])
        nm = NAMES.get(k) or NAMES.get(a["name"])
        if nm and not a.get("name_ru"):
            a["name_ru"] = nm[0]
            names_done += 1
        if a.get("desc_ru"):
            continue
        desc = DESCS.get(k) or DESCS.get(a["name"])
        if desc:
            a["desc_ru"] = desc
            descs_done += 1
            continue
        for pat, fn in TEMPLATES:
            m = pat.match(a["desc"])
            if m:
                ru = fn(m)
                if "None" not in ru:
                    a["desc_ru"] = ru
                    descs_done += 1
                    break
        if not a.get("desc_ru"):
            unresolved.append(a)
    return names_done, descs_done, unresolved


if __name__ == "__main__":
    nd, dd, left = apply()
    json.dump(data, open("payday/data/app_data.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("названий переведено:", nd)
    print("описаний переведено:", dd)
    print("осталось без перевода:", len(left))
    for a in left:
        print(f"  {a['name']}\t{a['desc']}")