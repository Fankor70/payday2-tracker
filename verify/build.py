# -*- coding: utf-8 -*-
"""Build bot_variants.json from the RU PAYDAY 2 Fandom wiki heist articles."""
import json, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(os.path.join(HERE, "raw_heists.json"), encoding="utf-8"))
tmpl = json.load(open(os.path.join(HERE, "tmpl_blocks.json"), encoding="utf-8"))
dload = json.load(open(os.path.join(HERE, "dlc_cats.json"), encoding="utf-8"))
cats = json.load(open(os.path.join(HERE, "cats.json"), encoding="utf-8"))["cats"]

WIKI = "https://payday.fandom.com/ru/wiki/"
URLEN = {}


def wiki_url(title):
    if title not in URLEN:
        import urllib.parse
        URLEN[title] = urllib.parse.quote(title.replace(" ", "_"), safe="")
    return WIKI + URLEN[title]


# ---------- wiki markup stripping ----------
def strip_templates(t):
    out, depth = [], 0
    i = 0
    while i < len(t):
        if t.startswith("{{", i):
            depth += 1; i += 2
        elif t.startswith("}}", i):
            depth = max(0, depth - 1); i += 2
        elif depth == 0:
            out.append(t[i]); i += 1
        else:
            i += 1
    return "".join(out)


def strip_markup(t):
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = strip_templates(t)
    # gallery / tabber / ref / file
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\[\[Файл:[^\]]*\]\]", " ", t, flags=re.I)
    t = re.sub(r"\[\[(?:w|wikipedia|Категория|en):[^\]]*\]\]", " ", t)
    t = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", t)   # links -> label
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)      # external links
    t = re.sub(r"\[https?://\S+\]", " ", t)
    t = t.replace("'''", "").replace("''", "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*\n\s*", " ", t)
    return t.strip()


def section(w, name):
    m = re.search(r"^==\s*" + re.escape(name) + r"\s*==\s*$", w, re.M)
    if not m:
        return ""
    j = w.find("\n== ", m.end())
    return w[m.end(): j if j > 0 else len(w)]


def lead_paragraph(w):
    """First prose paragraph of the article, for pages with no == Описание ==."""
    w = re.sub(r"\{\{Stub\}\}", "", w)
    w = re.sub(r"\{\{Ограбления PAYDAY 2[^}]*\}\}", "", w)
    w = re.sub(r"\{\{Цитата PAYDAY 2.*?\}\}", "", w, flags=re.S)
    w = re.sub(r"\{\{Инфобокс ограбления PD2.*?\n\}\}", "", w, flags=re.S)
    t = strip_markup(w.split("\n__NOTOC__")[0])
    for p in re.split(r"(?<=[.!?])\s+", t):
        p = p.strip()
        if len(p) > 40 and not p.startswith("|") and "{{" not in p:
            return p
    return t.strip()


def description_for(w):
    body = section(w, "Описание") or section(w, "Описание в игре")
    txt = strip_markup(body).strip() if body.strip() else ""
    if not txt:
        txt = lead_paragraph(w)
    return txt[:400]


# ---------- EN names ----------
def en_name(title, w):
    m = re.search(r"\{\{Ограбления PAYDAY 2\s*\|\s*([^|}\n]+)", w)
    if m and m.group(1).strip():
        return m.group(1).strip()
    m = re.search(r"\((?:ориг\.|англ\.)\s*([^)]+)\)", w)
    return m.group(1).strip() if m else ""


def tmpl_field(en, field):
    m = re.search(r"^\|\s*" + field + r"\s*=\s*(.+)$", tmpl.get(en, ""), re.M)
    return m.group(1).strip() if m else ""


def raw_infobox_field(w, field):
    m = re.search(r"^\|\s*" + field + r"\s*=\s*(.+)$", w, re.M)
    return m.group(1).strip() if m else ""


# ---------- hand-curated, evidence-backed variants ----------
BANK_DESC = ("Ограбление имеет четыре разновидности, которые можно различить, "
             "когда вы берётесь за контракт:")
BANK_INT = tmpl_field("Bank Heist", "int_name")

TRANSPORT_LOC_INT = tmpl_field("Transport", "int_name")
TRANSPORT_LOCS = [
    ("Парк", "Park", "arm_par (park)"),
    ("Гавань", "Harbor", "arm_fac (harbor)"),
    ("Центр города", "Downtown", "arm_hcm (downtown)"),
    ("Перекресток", "Crossroads", "arm_cro (crossroads)"),
    ("Проезд", "Underpass", "arm_und (underpass)"),
]

VARIANTS = {
    "Ограбление банка": dict(
        kind="loot",
        variants=[
            ("Деньги", "Cash", "branchbank_cash (cash)"),
            ("Ячейки", "Deposit", "branchbank_deposit(deposit)"),
            ("Золото", "Gold", "branchbank_gold_prof (gold)"),
            ("Случайное", "Random", "branchbank_prof (random)"),
        ],
        quote="== Описание == " + BANK_DESC + "\n# Деньги\n# Ячейки\n# Золото\n# Случайное",
        quote2="Шаблон:Ограбления PAYDAY 2 |int_name = " + BANK_INT,
    ),
    "Транспорт": dict(
        kind="map",
        variants=[(ru, en, hint) for ru, en, hint in TRANSPORT_LOCS],
        quote="== Описание == Ограбление имеет пять локаций. ... Происходить ограбление может "
              "на нескольких локациях:\n== Локации ==\n=== Парк ===\n=== Гавань ===\n"
              "=== Центр города ===\n=== Перекресток ===\n=== Проезд ===\n=== [[Ограбление поезда]] ===",
        quote2="Шаблон:Ограбления PAYDAY 2 |int_name = " + TRANSPORT_LOC_INT,
    ),
}

# heists that are one variant OF a shared parent entry
GROUPS = [
    dict(parent="The Bomb", parent_ru="Бомба", kind="map",
         note="Категория:The Bomb Heists содержит ровно Бомба: Доки и Бомба: Лес; int_name crojob1/crojob2/crojob3 + thebomb_stage_2/3 (общий корень crojob)",
         children=[("Бомба: Доки", "The Bomb: Dockyard", "crojob1 (job)/crojob2 (level)/thebomb_stage_2"),
                   ("Бомба: Лес", "The Bomb: Forest", "crojob2 (job)/crojob3 (level)/thebomb_stage_3")]),
    dict(parent="Пересечение границы", parent_ru="Пересечение границы", kind="map",
         note="int_name mex (job mex df.png) vs mex_cooking (job mex cooking df.png) — cooking/Christmas variant of the same map",
         children=[("Пересечение границы", "Border Crossing", "mex"),
                   ("Кристаллы на границе", "Border Crystals", "mex_cooking")]),
    dict(parent="Обучение", parent_ru="Обучение", kind="map",
         note="Категория:Обучение PAYDAY 2; both infoboxes carry |contract = 97 (same Crime.net contract slot)",
         children=[("Основы скрытности", "Flash Drive", "short1"),
                   ("Основы ведения боя", "Get the Coke", "short2")]),
    dict(parent="Armored Transport", parent_ru="Armored Transport", kind="map",
         note="Категория:Armored Transport; Train Heist is listed inside Транспорт's == Локации == section",
         children=[("Транспорт", "Transport", "arm_cro/arm_hcm/arm_fac/arm_par/arm_und"),
                   ("Ограбление поезда", "Train Heist", "arm_for")]),
    dict(parent="The Point Break Heists", parent_ru="Набор The Point Break", kind="map",
         note="Категория:The Point Break Heists; shared int_name prefix pbr",
         children=[("Рождение небес", "Birth of Sky", "pbr2"),
                   ("У подножия горы", "Beneath the Mountain", "pbr")]),
    dict(parent="Hardcore Henry Heists", parent_ru="Набор Hardcore Henry", kind="map",
         note="Категория:Hardcore Henry Heists (Darkcore/Henry — «Хадкорк Хенри» отсутствует как статья)",
         children=[("Станция Murkywater", "Murky Station", "dark"),
                   ("Точка кипения", "Boiling Point", "mad")]),
    dict(parent="John Wick Heists", parent_ru="Набор John Wick", kind="map",
         note="Категория:John Wick Heists",
         children=[("Бруклин 10-10", "Brooklyn 10-10", "spa"),
                   ("Яхта", "The Yacht Heist", "fish")]),
]

child_of = {}
for g in GROUPS:
    for ru, en, hint in g["children"]:
        child_of[ru] = dict(parent=g["parent_ru"], parent_en=g["parent"], hint=hint, note=g["note"])

# ---------- build ----------
heists = []
for title in sorted(raw):
    w = raw[title]
    en = en_name(title, w)
    desc = description_for(w)
    entry = dict(title=title, name_en=en, has_variants=False, variants=[],
                 variant_kind="none", description_ru=desc, wiki_url=wiki_url(title))

    if title in VARIANTS:
        v = VARIANTS[title]
        entry["has_variants"] = True
        entry["variant_kind"] = v["kind"]
        entry["variants"] = [
            dict(ru=ru, en_hint=en_h, source_quote=v["quote"],
                 source_quote_2=v["quote2"], int_name=hint)
            for ru, en_h, hint in v["variants"]
        ]
    elif title in child_of:
        c = child_of[title]
        entry["has_variants"] = True
        entry["variant_kind"] = "map"
        entry["is_variant_of"] = c["parent"]
        entry["variants"] = [dict(ru=title, en_hint=en, source_quote=c["note"], int_name=c["hint"])]

    ic = [c for c in cats.get(title, []) if c.startswith("Категория:") and c != "Категория:Ограбления PAYDAY 2"
          and c != "Категория:PAYDAY 2"]
    entry["categories"] = ic
    entry["infobox_int_name"] = tmpl_field(en, "int_name") or raw_infobox_field(w, "int_name")
    entry["infobox_contract"] = tmpl_field(en, "contract") or raw_infobox_field(w, "contract")
    heists.append(entry)

out = dict(generated="2026-10-10", source="https://payday.fandom.com/ru/wiki/"
                                         "Категория:Ограбления_PAYDAY_2",
           heist_count=len(heists),
           notes=[
               "Единственный шаблон {{Description3}} на вики отсутствует — варианты закодированы в prose, "
               "в списках под == Описание ==, в секции == Локации == и в поле |int_name шаблона «Ограбления PAYDAY 2».",
               "|int_name в Шаблон:Ограбления PAYDAY 2 — надёжный признак варианта: несколько int_name в одном блоке "
               "с общим корнем = loot/map-варианты (branchbank_*, arm_*).",
               "Поле |contract в инфобоксе группирует по доске контрактов (job board), а не по вариантам: "
               "например contract=6 объединяет Пересечение границы, Кристаллы на границе, Рождение небес, "
               "У подножия горы, Белый дом и др. — они НЕ являются вариантами друг друга.",
               "«Варка мета» = Cook Off (int_name=rat, собственная карта). Это НЕ Hardcore Henry «Rack 'Em» "
               "и не переиспользует карту Станции Murkywater (int_name=dark). Статьи «Rack 'Em» на ru-вики нет.",
               "Категория:Hardcore Henry Heists содержит только Станцию Murkywater (dark) и Точку кипения (mad); "
               "«Варка мета» в неё не входит.",
               "У.authoritative признак DLC-группы — общая категория вида «Категория:The Bomb Heists», "
               "«Категория:The Point Break Heists», «Категория:John Wick Heists», "
               "«Категория:Hardcore Henry Heists», «Категория:Обучение PAYDAY 2», «Категория:Armored Transport».",
               "Магазины (Ювелирный магазин / Магазин бриллиантов / Автосалон / Четыре магазина) НЕ объединены "
               "вики ни в одну группу: у каждого свой int_name (jewelry_store / family / cage / four_stores) "
               "и нет общего родителя. В игре они — карты одного контракта Shops, но вики этого не утверждает.",
           ],
           heists=heists,
           variant_groups=[dict(parent_ru=g["parent_ru"], parent_en=g["parent"],
                                kind=g["kind"], evidence=g["note"],
                                children=[c[0] for c in g["children"]],
                                children_en=[c[1] for c in g["children"]])
                           for g in GROUPS])

p = os.path.join(HERE, "bot_variants.json")
json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("heists:", len(heists), "| with variants:", sum(1 for h in heists if h["has_variants"]))