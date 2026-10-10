import io

p = "fetch_en_heist_ach.py"
lines = io.open(p, encoding="utf-8").read().split("\n")

good = r'    m = re.search(HEAD, txt, re.I | re.M)'
bad_end = next(i for i, l in enumerate(lines)
               if l.startswith(']*Achievements[^='))

out = []
for i, l in enumerate(lines):
    if i == bad_end - 2:                       # the correct line already inserted
        continue
    if i >= bad_end - 1 and lines[i].strip() != "if not m:":
        continue
    out.append(l)

io.open(p, "w", encoding="utf-8").write("\n".join(out))

# define HEAD once, above the function
t = io.open(p, encoding="utf-8").read()
if "HEAD =" not in t:
    t = t.replace("def achievements_section(txt):",
                  '# the heading varies a lot across heist pages\n'
                  'HEAD = re.compile(r"^==[^=\\n]*\\bAchievements\\b[^=\\n]*==", re.I | re.M)\n\n\n'
                  "def achievements_section(txt):")
    io.open(p, "w", encoding="utf-8").write(t)

print(io.open(p, encoding="utf-8").read().split("\n")[62:78].__str__())