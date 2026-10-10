# -*- coding: utf-8 -*-
"""Match the player's Steam achievement list onto our achievement rows.

PAYDAY 2 mirrors its whole in-game achievement system to Steam, so the public
Steam profile page lists the same 1342 rows. That is far easier to read than the
encrypted save file and always matches the game's own naming.
"""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

done_names = json.load(open("payday/data/steam_unlocked.json", encoding="utf-8"))
data = json.load(open("payday/data/app_final.json", encoding="utf-8"))
A = data["achievements"]


def norm(s):
    s = (s or "").lower().replace("’", "'").replace("–", "-")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


index = {}
for a in A:
    index.setdefault(norm(a["name"]), a["id"])

done_ids, missed = set(), []
for n in done_names:
    i = index.get(norm(n))
    if i is None:
        missed.append(n)
    else:
        done_ids.add(i)

data["done_ids"] = sorted(done_ids)
data["progress_source"] = {
    "type": "steam_profile",
    "count": len(done_ids),
    "total": len(A),
}
json.dump(data, open("payday/data/app_final.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

print("в Steam отмечено:", len(done_names))
print("сопоставлено с базой:", len(done_ids), "из", len(A),
      f"({round(len(done_ids)/len(A)*100)}%)")
if missed:
    print("не нашлось в базе:", len(missed))
    for n in missed[:15]:
        print("   -", n)

# where the progress sits
by_cat = {}
for i in done_ids:
    by_cat[A[i]["category"]] = by_cat.get(A[i]["category"], 0) + 1
print("\nпо категориям:")
for k, v in sorted(by_cat.items(), key=lambda x: -x[1]):
    print(f"   {v:4d}  {k}")