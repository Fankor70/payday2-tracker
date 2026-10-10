import json, re, os, difflib

BASE = os.path.dirname(os.path.abspath(__file__))


def split_top(s):
    parts = []
    depth = 0
    cur = ''
    k = 0
    while k < len(s):
        if s.startswith('{{', k):
            depth += 1; cur += '{{'; k += 2; continue
        if s.startswith('}}', k):
            depth -= 1; cur += '}}'; k += 2; continue
        if s[k] == '|' and depth == 0:
            parts.append(cur); cur = ''; k += 1; continue
        cur += s[k]; k += 1
    parts.append(cur)
    return [re.sub(r'\s+', ' ', p).strip() for p in parts]


def ach_templates(txt):
    pat = '{{Achievement|'
    res = []
    i = 0
    while True:
        s = txt.find(pat, i)
        if s < 0:
            break
        depth = 0; j = s
        while j < len(txt):
            if txt.startswith('{{', j):
                depth += 1; j += 2
            elif txt.startswith('}}', j):
                depth -= 1; j += 2
                if depth == 0:
                    break
            else:
                j += 1
        res.append(split_top(txt[s + len(pat):j - 2]))
        i = j
    return res


def subfn(t):
    return os.path.join(BASE, 'sub', 'Achievements_Payday_2_%s.wiki' % re.sub(r'[^A-Za-z0-9]+', '_', t))


def hpfn(t):
    return os.path.join(BASE, 'hp', re.sub(r'[^A-Za-z0-9]+', '_', t) + '.wiki')


def clean(s):
    s = re.sub(r'</?nowiki>', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def norm(s):
    s = s.lower().replace('\u2019', '').replace('\u2018', '')
    s = re.sub(r"[^a-z0-9]+", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


d = json.load(open(os.path.join(BASE, '..', 'data', 'app_final.json'), encoding='utf-8'))
ach = {a['id']: a for a in d['achievements']}
hmap = {h['page']: h for h in d['heists']}

PAGES = ['GO Bank', 'Diamond Heist (Payday 2)', 'Heat Street (Payday 2)', 'Bank Heist', 'Transport',
         'First World Bank (Payday 2)', 'No Mercy (Payday 2)', 'Panic Room (Payday 2)',
         'Slaughterhouse (Payday 2)', 'Counterfeit (Payday 2)', 'Undercover (Payday 2)',
         'Green Bridge (Payday 2)', 'Art Gallery', 'Boiling Point', 'Murky Station',
         'The Big Bank', 'Brooklyn 10-10', 'The Diamond', 'Hotline Miami']

NOTES = {
 'GO Bank': 'Heist page carries an inline 9-entry table AND transcludes "Achievements (Payday 2)/GO Bank" (10 entries, 3 of them duplicates); the union (16 unique) is the authoritative list. Clean.',
 'Diamond Heist (Payday 2)': 'Heist page transcludes "Achievements (Payday 2)/DiamondHeist" (11 unique). All 17 false positives belong to the SEPARATE heist "The Diamond" (13 of them) or are "Holdout wave" achievements (4) that the wiki achievements pages do not document at all.',
 'Heat Street (Payday 2)': 'The wiki has NO achievements subpage for Heat Street; the authoritative list is the inline achievement table of heist page "Heat Street (Payday 2)" (11). 12 of the 16 false positives are Brooklyn 10-10 achievements (a different heist, see the Brooklyn 10-10 row), 4 are Holdout-wave achievements absent from the wiki. No genuinely missing entries.',
 'Bank Heist': 'No dedicated subpage; the authoritative list is the inline table of heist page "Bank Heist" (35 entries). All 14 false positives are Holdout-wave achievements that belong to First World Bank / San Martin Bank / Big Bank and that the wiki achievements pages do not list. MISSING: "A Good Haul" (any Branch Bank job, secure loot worth at least $400.000) is on the wiki heist page but has no id in heists[].ids.',
 'Transport': 'No subpage matches the Transport heist page ("Achievements (Payday 2)/ArmoredTransport" holds only 22 of the 43). False positives are Transport: Train Heist achievements (a sibling heist the dataset lists separately), 5 global mask/weapon achievements (Heat Around the Corner, License to Kill, Affordable Healthcare, I am Not a Crook!, Fool Me Once..., I Did Not Have Sexual Relations With That Bulldozer) and 2 entries that are real in-game achievements the wiki heist page simply omits/spells differently ("All The Noise and The Hurry"; "Urban Hiking" = wiki "Urban Hikeing", wiki also lists both "Making My Way Downtown" and "Makin\' My Way Downtown").',
 'First World Bank (Payday 2)': 'No dedicated subpage; authoritative list is the inline table of the heist page (17). All 4 false positives are Holdout-wave achievements that the wiki does not document.',
 'No Mercy (Payday 2)': 'Heist page transcludes "Achievements (Payday 2)/No Mercy" (12 entries, 1 duplicate, 11 unique). Clean.',
 'Panic Room (Payday 2)': 'Heist page transcludes "Achievements (Payday 2)/Panic Room" (13 entries, 1 duplicate, 12 unique). Clean.',
 'Slaughterhouse (Payday 2)': 'No dedicated subpage; authoritative list is the inline table of heist page "Slaughterhouse (Payday 2)" (13). Clean. ("Achievements (Payday 2)/TSIRRDay3" is a mixed DLC-day page, not heist specific.)',
 'Counterfeit (Payday 2)': 'No dedicated subpage; authoritative list is the inline table of heist page "Counterfeit (Payday 2)" (13). Clean. ("Achievements (Payday 2)/Wolf Pack" only holds the Death Wish subset.)',
 'Undercover (Payday 2)': 'No dedicated subpage; authoritative list is the inline table of heist page "Undercover (Payday 2)" (13). Clean.',
 'Green Bridge (Payday 2)': 'No dedicated subpage; authoritative list is the inline table of heist page "Green Bridge (Payday 2)" (13 entries, "I Felt Bad For Him" duplicated). Effectively clean - the only difference from the dataset is punctuation/capitalisation of "Jack the Ripper\'s Prison Slippers!" vs "Jack the Rippers, Prison Slippers!".',
 'Art Gallery': 'No dedicated subpage; authoritative list is the inline table of heist page "Art Gallery" (12). Clean.',
 'Boiling Point': 'No dedicated subpage; authoritative list is the inline table of heist page "Boiling Point" (14). MISSING: "This is WAR Baby!" (complete Boiling Point on Death Sentence with One Down) is on the wiki but has no id in heists[].ids. Also note "Red Snow" is shared with the Hardcore Henry page.',
 'Murky Station': 'No dedicated subpage; authoritative list is the inline table of heist page "Murky Station" (18 entries, 4 duplicates, 14 unique). Clean. ("Achievements (Payday 2)/Hardcore Henry" holds only 13 and mixes in Henry\'s Rock.)',
 'The Big Bank': 'Checked as a companion of Bank Heist. Heist page transcludes "Achievements (Payday 2)/Big Bank" and adds 3 inline entries (18 unique). False positives are Holdout-wave achievements of other banks.',
 'Brooklyn 10-10': 'Checked as a companion of Heat Street. No dedicated subpage; authoritative list is the inline table of heist page "Brooklyn 10-10" (11). All 15 false positives are Heat Street achievements.',
 'The Diamond': 'Checked as the heist the Diamond Heist false positives really belong to. Heist page transcludes "Achievements (Payday 2)/The Diamond Heist" (7 unique) and adds 7 inline entries (13 unique). All 14 false positives are Diamond Heist (Payday 2) achievements plus Holdout-wave achievements.',
 'Hotline Miami': 'Heist page transcludes "Achievements (Payday 2)/Hotline Miami" (8 unique) and adds 7 inline entries (14 unique). MISSING: "+1 (786) 519-3708" (Hotline Miami pro job on Death Wish). The one false positive is a name-only difference ("*Click*").',
}

rows = []
tf = 0
tm = 0
for p in PAGES:
    ht = open(hpfn(p), encoding='utf-8').read()
    tl = re.findall(r'\{\{:Achievements \(Payday 2\)/([^}|]+)', ht)
    subpage = tl[0] if tl else None
    wikinames = [clean(x[0]) for x in ach_templates(ht)]
    if subpage:
        wikinames += [clean(x[0]) for x in ach_templates(open(subfn(subpage), encoding='utf-8').read())]
    seen = {}
    order = []
    for n in wikinames:
        k = norm(n)
        if k and k not in seen:
            seen[k] = n
            order.append(k)
    ids = hmap[p]['ids']
    dsn = [ach[i]['name'] for i in ids]
    dsn_n = [norm(x) for x in dsn]
    used_wiki = set()
    fps = []
    for idx, (i, n) in enumerate(zip(ids, dsn)):
        k = dsn_n[idx]
        if k in seen:
            used_wiki.add(k)
            continue
        cand = difflib.get_close_matches(k, order, n=1, cutoff=0.86)
        if cand and cand[0] not in used_wiki:
            used_wiki.add(cand[0])
        else:
            fps.append({'id': i, 'name': n})
    missing = []
    for k in order:
        if k in used_wiki:
            continue
        cand = difflib.get_close_matches(k, dsn_n, n=1, cutoff=0.86)
        if not cand:
            missing.append(seen[k])
    tf += len(fps)
    tm += len(missing)
    rows.append({'page': p, 'wiki_subpage': subpage, 'dataset_count': len(ids),
                 'wiki_count': len(order), 'ok': (not fps and not missing),
                 'false_positives': fps, 'missing': missing, 'note': NOTES.get(p, '')})

out = {'generated': '2026-10-10', 'heists_checked': len(rows), 'heists': rows,
       'summary': {'total_false_positives': tf, 'total_missing': tm}}
path = os.path.join(BASE, 'bot_en.json')
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('heists', len(rows), 'FP', tf, 'MISS', tm)
for r in rows:
    print('%-26s ds=%-3d wiki=%-3d ok=%-5s FP=%-3d MISS=%d %s' % (
        r['page'], r['dataset_count'], r['wiki_count'], r['ok'],
        len(r['false_positives']), len(r['missing']), r['missing']))