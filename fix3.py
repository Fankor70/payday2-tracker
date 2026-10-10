import io

p = "fetch_en_heist_ach.py"
lines = io.open(p, encoding="utf-8").read().split("\n")

# lines[70] and [71] (0-based) are the two fragments of the broken regex
assert lines[70].startswith("]*Achievements[^="), repr(lines[70])
assert lines[71].startswith(']*==", txt'), repr(lines[71])

del lines[70:72]
io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines[64:76]))