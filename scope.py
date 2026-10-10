# -*- coding: utf-8 -*-
"""Classify an achievement by WHERE it can be done: heist / lobby / anywhere.

The tracker needs this because "Spend $1,000,000 in total cash" is a safe-house
task and belongs nowhere near a heist run, while "Kill 100 cops with AK or CAR"
is exactly the sort of thing you grind in parallel with any heist.
"""
import re

# order matters: first match wins, so put the specific ones first
RULES = [
    # ---------------- safe house / menus ----------------
    ("lobby", r"\bbuy (?:a|an|the)\b|\bpurchase\b|\bmodify (?:a|an|the)\b|"
              r"\bown \d+|\bequip (?:an?|the)\b|\bspend \$|\bspend \d|"
              r"\badd money to\b|\bearn (?:a|an|one)\b|\bcrates?\b|\bstamp\b|"
              r"\bcustomi[sz]e\b|\breturn\b|\bsell\b|"
              r"\bunlock(?:ing)? (?:the )?(?:ability|perk|skill|drill)\b|"
              r"\bon your crew\b|\bwith a player who\b|\bfriends?\b|"
              r"\bмодифицируй\b|\bприобр[её]т[ий]\b|\bпотра[тьт]\b|\bкупи\b|\bнад[её]н\b|"
              r"\bдобавь деньги\b|\bзаработай\b|\bэкипируй\b|\bпосылк|\bконтейнер"),
    ("lobby", r"^(?:until|wear|put on|equip)\b.*\bmask\b"),
    # ---------------- reputation / progress from heists ----------------
    ("heist", r"\breach reputation level\b|\breputation level\b|"
              r"\breach infamy\b|\breach level\b|\bgain a level\b|"
              r"\breach character level\b|"
              r"\bрепутаци|\bуровн[ьия] (?:репутации|персонажа)|\bдостигни уровн"),
    # ---------------- definite in-heist actions ----------------
    ("heist", r"\bkill\b|\bkills\b|\bdefeat\b|\beliminate\b|\bdestroy\b|\bsurvive\b|"
              r"\bcomplete (?:a|an|the|your|this|all)\b|\bcomplete \d+ (?:of )?(?:bain|locke|vlad|hector|jimmy|the)\b|"
              r"\bfinish (?:a|the)\b|\bescape\b|\bobjective\b|\bsecure \d+|\bbags?\b|"
              r"\bsteal\b|\bsecure the\b|\bcomplete a heist\b|\bany heist\b|\bday of a heist\b|"
              r"\bdo not die\b|\bdon'?t die\b|\bsurvive\b|\bhostage\b|\banswer the\b|"
              r"\bуби[йт]|скрой|заверши|укра[дё]|вынеси|мешк|цел[ьи]|доживи|"
              r"\bне умира|\bне уб[ий]|\bне прыга|\bне стреляй|выполн"),
    ("heist", r"\bwhile (?:wearing|using|in)\b|\busing only\b|\bwith (?:a|the|your)\b.*\b(?:rifle|pistol|shotgun|smg|sniper|lmg)\b|"
              r"\bequipped\b|\bcarry\b|\bbag\b"),
    # ---------------- anywhere ----------------
    ("anywhere", r"^jump\.?\b|\buntil i put on the mask\b"),
]

# achievements that only exist in the safe house by definition
LOBBY_HINTS = ("safe house", "safehouse", "лубби", "убежищ")


def scope_of(desc):
    t = (desc or "").lower()
    if not t:
        return "heist"
    for scope, pat in RULES:
        if re.search(pat, t):
            return scope
    return "heist"


def annotate(achievements):
    """Add a `scope` field, then re-check the ones that fall back to heist."""
    for a in achievements:
        a["scope"] = scope_of(a.get("desc"))
        d = (a.get("desc") or "").lower()
        # "in the safe house" means the task happens in the lobby -- but the heist
        # "Safe House Nightmare" also contains the words, so only trust the hint
        # when the text does not talk about a job/contract at all
        runs_a_heist = re.search(
            r"\b(?:job|heist|contract|mission|day of)\b|контракт", d)
        if any(h in d for h in LOBBY_HINTS) and not runs_a_heist:
            a["scope"] = "lobby"
        elif runs_a_heist:
            a["scope"] = "heist"
    return achievements