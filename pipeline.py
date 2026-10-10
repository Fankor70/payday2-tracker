# -*- coding: utf-8 -*-
"""Full rebuild. Each stage reads the previous stage's file, never its own output."""
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

STEPS = [
    ("payday/parse_ach.py", "разбор шаблонов {{Achievement}} (EN)"),
    ("payday/build_dataset.py", "структурирование: хайсты, сложности, награды"),
    ("payday/parse_ru.py", "разбор и слияние русской вики"),
    ("payday/parse_heists.py", "реестр хайстов"),
    ("payday/build_v2.py", "структура: хайсты, сложности, награды"),
    ("payday/translate.py", "перевод оставшихся названий и описаний"),
    ("payday/build_ru_linked.py", "данные из раздела «Связанные достижения» русской вики"),
    ("payday/build_v3.py", "русские хайсты, план заходов, лобби/хайст"),
    ("payday/build_variants.py", "разновидности, карты, дни, слияния"),
    ("payday/build_final.py", "финальная сборка"),
    ("payday/build_progress.py", "прогресс из профиля Steam"),
    ("payday/apply_wiki_attribution.py", "привязка хайстов по данным вики"),
    ("payday/fix_attribution.py", "разметка «своё / можно дополнительно»"),
    ("payday/app/apply_crew4.py", "разметка достижений на полный состав"),
    ("payday/app/categorize.py", "разбивка на категории планирования"),
    ("payday/app/build_route.py", "маршрут: заход + общие счётчики"),
    ("payday/app/build_targets.py", "числовые цели достижений"),
    ("payday/app/build_ui.py", "страница приложения"),
    ("payday/build_html.py", "страница-файл"),
]

for script, label in STEPS:
    r = subprocess.run([sys.executable, script], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("СБОЙ:", script)
        print(r.stdout[-2500:])
        print("STDERR:", r.stderr[-2500:])
        sys.exit(1)
    out = [ln for ln in r.stdout.strip().splitlines()
           if ln.strip() and not ln.startswith("  - ")]
    print("\n" + "=" * 66)
    print(">>", label)
    print("=" * 66)
    print("\n".join(out[-14:]))