# -*- coding: utf-8 -*-
"""Shared MediaWiki template helpers (no side effects on import)."""
import re


def split_params(body):
    """Split on top-level pipes, ignoring pipes inside [[wiki links]]."""
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
    """Return [(start, end, params)] for every {{name|...}} using brace matching."""
    res = []
    for m in re.finditer(r'\{\{\s*' + re.escape(name) + r'\s*[|\}]', text):
        if text[m.end() - 1] == '}':
            continue
        i, depth = m.end(), 1
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        if depth == 0:
            res.append((m.start(), i, split_params(text[m.end():i - 1])))
    return res


def _strip_templates(s):
    for _ in range(4):
        new = re.sub(r"\{\{[Cc][Oo][Ll][Oo][Rr]\|[^|{}]*\|([^{}]*)\}\}", r"\1", s)
        if new == s:
            break
        s = new
    return re.sub(r"\{\{[^{}]*\}\}", " ", s)


def clean(s):
    s = _strip_templates(s.strip())
    s = re.sub(r'\{\{(lc|lc:)[:|][^}]*\}\}', '', s)
    s = re.sub(r"\{\{nowrap\|([^}]*)\}\}", r'\1', s)
    s = re.sub(r"\{\{winky\}\}", '', s)
    s = re.sub(r'\[\[[^\|\]]*\|([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'\[\[([^\]]*)\]\]', r'\1', s)
    s = re.sub(r"'{2,}", '', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('\xa0', ' ').replace('&nbsp;', ' ').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', s).strip()
# -*- coding: utf-8 -*-
"""Shared MediaWiki template helpers (no side effects on import)."""
import re


def split_params(body):
    """Split on top-level pipes, ignoring pipes inside [[wiki links]]."""
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
    """Return [(start, end, params)] for every {{name|...}} using brace matching."""
    res = []
    for m in re.finditer(r'\{\{\s*' + re.escape(name) + r'\s*[|\}]', text):
        if text[m.end() - 1] == '}':
            continue
        i, depth = m.end(), 1
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        if depth == 0:
            res.append((m.start(), i, split_params(text[m.end():i - 1])))
    return res


def clean(s):
    s = s.strip()
    s = re.sub(r'\{\{color\|[^|]*\|([^|]*)\}\}', r'\1', s)
    s = re.sub(r'\{\{(lc|lc:)[:|][^}]*\}\}', '', s)
    s = re.sub(r"\{\{nowrap\|([^}]*)\}\}", r'\1', s)
    s = re.sub(r"\{\{winky\}\}", '', s)
    # leftover template params that leaked through as [[image = file.jpg]]
    s = re.sub(r'\[\[\s*(?:image|img|file)\s*=\s*[^\]]*\]\]', '', s, flags=re.I)
    s = re.sub(r'\[\[([^\|\]]*)\|([^\]]*)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]*)\]\]', r'\1', s)
    s = re.sub(r"'''?", '', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&nbsp;', ' ').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', s).strip()