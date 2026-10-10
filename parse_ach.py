import json, re

def split_params(body):
    """Split template body on top-level pipes.

    A pipe inside a [[wiki link]] is part of the link syntax, not a parameter
    separator -- without tracking link depth every description containing
    [[Page|Display text]] would be truncated at that pipe.
    """
    out, depth, link, cur = [], 0, 0, []
    i, n = 0, len(body)
    while i < n:
        if body.startswith('[[', i):
            link += 1; cur.append('[['); i += 2; continue
        if body.startswith(']]', i) and link:
            link -= 1; cur.append(']]'); i += 2; continue
        ch = body[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        if ch == '|' and depth == 0 and link == 0:
            out.append(''.join(cur)); cur = []
        else:
            cur.append(ch)
        i += 1
    out.append(''.join(cur))
    return out

def find_templates(text, name):
    """Yield (start, end, params) for every {{name|...}} with brace matching."""
    res = []
    for m in re.finditer(r'\{\{\s*' + re.escape(name) + r'\s*\|', text):
        i = m.end(); depth = 1; start = m.start()
        while i < len(text) and depth > 0:
            c = text[i]
            if c == '{': depth += 1
            elif c == '}': depth -= 1
            i += 1
        if depth == 0:
            res.append((start, i, split_params(text[m.end():i-1])))
    return res

def _strip_templates(s):
    """Unwrap {{color|...}} repeatedly, then drop anything still malformed."""
    for _ in range(4):
        new = re.sub(r"\{\{[Cc][Oo][Ll][Oo][Rr]\|[^|{}]*\|([^{}]*)\}\}", lambda m: m.group(1), s)
        if new == s:
            break
        s = new
    s = re.sub(r"\{\{[^{}]*\}\}", " ", s)
    # a template the wiki cut off mid-token, e.g. "... выше.{{co"
    s = re.sub(r"\{\{[^{}]*$", "", s)
    s = re.sub(r"\{\{[^|{}|]{0,40}$", "", s)
    return s


def clean(s):
    s = _strip_templates(s.strip())
    s = re.sub(r'\{\{(lc|lc:)[:|][^}]*\}\}', '', s)
    s = re.sub(r"\{\{nowrap\|([^}]*)\}\}", lambda m: m.group(1), s)
    s = re.sub(r"\{\{winky\}\}", '', s)
    s = re.sub(r'\[\[[^\|\]]*\|([^\]]*)\]\]', lambda m: m.group(1), s)
    s = re.sub(r'\[\[([^\]]*)\]\]', lambda m: m.group(1), s)
    s = re.sub(r"'{2,}", '', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('\xa0', ' ').replace('&nbsp;', ' ').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', s).strip()


raw = json.load(open('payday/data/subpages.json', encoding='utf-8'))
master = open('payday/data/pd2_achievements.wikitext', encoding='utf-8').read()

items = []
def add(text, source):
    for (s, e, p) in find_templates(text, 'Achievement'):
        if len(p) < 3: continue
        name, img, desc = p[0], p[1], p[2]
        items.append({
            'name': clean(name),
            'desc': clean(desc),
            'source': source,
            'raw': desc,
        })

add(master, '__master__')
for k, v in raw.items():
    add(v, k)

# dedupe by (name, desc)
seen, uniq = set(), []
for it in items:
    key = (it['name'].lower(), it['desc'].lower()[:80])
    if key in seen: continue
    seen.add(key); uniq.append(it)

print('parsed', len(items), '-> unique', len(uniq))
json.dump(uniq, open('payday/data/ach_parsed.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
c = Counter(x['source'] for x in uniq)
print('sources:', len(c))
for k, v in c.most_common(30): print(f'  {v:4d}  {k}')
