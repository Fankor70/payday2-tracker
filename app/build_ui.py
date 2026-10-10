# -*- coding: utf-8 -*-
"""Build the app's UI: the tracker page plus the import panel and live wiring."""
import json, io, os, re, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import version
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = os.path.join(os.path.dirname(HERE), "data", "app_final.json")
DATA = json.load(open(SRC, encoding="utf-8"))
steam = {a["name"]: a for a in
         json.load(open(os.path.join(os.path.dirname(HERE), "data", "steam_parsed.json"),
                        encoding="utf-8"))}

slim = []
for a in DATA["achievements"]:
    slim.append({
        "i": a["id"], "n": a["name"], "nr": a.get("name_ru"),
        "d": a["desc"], "dr": a.get("desc_ru"), "p": a.get("pct"),
        "img": steam.get(a["name"], {}).get("img", ""),
        "h": a.get("heists") or [], "df": a.get("difficulties") or [],
        "r": a.get("rewards") or {}, "c": a.get("category"),
        "sc": a.get("scope"), "dy": a.get("day"),
        "dp": a.get("deps") or [], "fit": a.get("fit"),
    })
PAYLOAD = {"achievements": slim, "heists": DATA["heists"],
           "parallel": DATA.get("parallel", {}),
           "global_ids": DATA.get("global_ids", []),
           "category_labels": DATA["category_labels"],
           "category_priority": DATA["category_priority"],
           "route_meta": DATA.get("route_meta") or {}}

UI = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PAYDAY 2 — Трекер достижений</title>
<style>
  :root{--bg:#0b0d10;--panel:#14171c;--panel2:#1a1e25;--line:#272d36;--txt:#e8ebf0;
    --dim:#8a94a3;--acc:#f0a020;--acc2:#e2574c;--ok:#3fb950;--blue:#58a6ff;--purple:#a371f7}
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--txt);font:14px/1.5 "Segoe UI",Roboto,Arial,sans-serif;
    display:flex;flex-direction:column}
  a{color:var(--blue)}
  header{background:linear-gradient(90deg,#1c1510,#14171c);border-bottom:1px solid var(--line);
    padding:9px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:sticky;top:0;z-index:30}
  header h1{font-size:15px;margin:0;color:var(--acc)}
  header h1 small{color:var(--dim);font-weight:400;margin-left:7px;font-size:12px}
  .stat{font-size:12px;color:var(--dim)} .stat b{color:var(--txt);font-size:14px}
  .grow{flex:1}
  button,input[type=search],input[type=text]{background:var(--panel2);color:var(--txt);
    border:1px solid var(--line);border-radius:6px;padding:6px 10px;font:inherit;font-size:13px}
  button{cursor:pointer} button:hover{border-color:var(--acc)}
  button.on{background:var(--acc);color:#12100c;font-weight:600}
  button.go{background:#1d3a26;border-color:#2f5138;color:#9fdfb0}
  button.danger{background:#2a1516;border-color:#4a2626;color:#e0a3a0}
  input[type=search]{cursor:text;min-width:170px}

  #importbar{display:none;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 16px;
    background:#111820;border-bottom:1px solid var(--line)}
  #importbar.show{display:flex}
  #importbar .msg{font-size:12px;color:var(--dim)}
  #importbar .msg.ok{color:var(--ok)} #importbar .msg.err{color:var(--acc2)}
  #live{font-size:11px;padding:2px 8px;border-radius:9px;border:1px solid var(--line);color:var(--dim)}
  #live.on{border-color:#2f5138;color:var(--ok);background:#111a15}
  #btn-auto.live{border-color:#2f5138;color:#9fdfb0;background:#111a15}
  #btn-auto.checking{border-color:#4a3a20;color:var(--acc)}
  #steam-when{font-size:11px}
  #steam-when.bad{color:var(--acc2)}

  #wrap{flex:1;display:flex;min-height:0}
  #side{width:320px;flex-shrink:0;border-right:1px solid var(--line);background:var(--panel);
    display:flex;flex-direction:column;min-height:0;position:relative}
  #side .bar{padding:9px;border-bottom:1px solid var(--line);display:grid;gap:6px;overflow:hidden}
  #side .bar input{width:100%}
  #heistlist{overflow-y:auto;flex:1;min-height:0;padding-bottom:40px}
  #achresults{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;padding:6px 0 40px}
  #achresults *{min-width:0;max-width:100%}
  .ares{display:block;width:100%;max-width:100%;box-sizing:border-box;text-align:left;background:none;
    border:0;border-bottom:1px solid var(--line);border-radius:0;padding:8px 12px;cursor:pointer;
    color:var(--txt);overflow:hidden;overflow-wrap:anywhere;word-break:break-word}
  .ares:hover{background:var(--panel2)} .ares .an{font-size:13px;font-weight:600}
  .ares .an em{color:var(--acc);font-style:normal}
  .ares .aw{font-size:11px;color:var(--dim);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .ares .ac{font-size:11.5px;color:var(--dim);margin-top:1px;overflow-wrap:anywhere;
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .grp{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--dim);
    padding:11px 12px 4px;font-weight:700}
  .hitem{display:flex;align-items:center;gap:7px;padding:6px 12px;cursor:pointer;border-left:3px solid transparent}
  .hitem:hover{background:var(--panel2)} .hitem.sel{background:#232932;border-left-color:var(--acc)}
  .hitem .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}
  .hitem .rn{font-size:10.5px;padding:1px 6px;border-radius:9px;border:1px solid var(--line);
    color:var(--dim);flex-shrink:0;font-variant-numeric:tabular-nums}
  .hitem .rn.many{color:var(--acc2);border-color:#4a2626}
  .bar-mini{height:3px;background:var(--line);border-radius:2px;width:34px;overflow:hidden;flex-shrink:0}
  .bar-mini i{display:block;height:100%;background:var(--ok)}
  .pill{font-size:10px;padding:0 5px;border-radius:8px;border:1px solid var(--line);color:var(--dim)}
  .pill.st{color:var(--blue)} .pill.ld{color:var(--acc2)}

  #main{flex:1;overflow-y:auto;min-width:0;display:flex;flex-direction:column}
  #maininner{display:grid;grid-template-columns:minmax(0,1fr) 400px;flex:1;min-height:0}
  @media (max-width:1200px){#maininner{grid-template-columns:minmax(0,1fr)}}
  .colmain{overflow-y:auto;padding:16px 20px 90px;min-width:0}
  .colside{overflow-y:auto;padding:16px 14px 90px;min-width:0;border-left:1px solid var(--line);background:#0f1216}
  @media (max-width:1200px){.colside{border-left:0;border-top:1px solid var(--line)}}
  .topbar{display:grid;grid-template-columns:1fr 210px;border-bottom:1px solid var(--line);
    background:linear-gradient(90deg,#1c1510,#14171c)}
  .topbar .cellname{padding:11px 20px;border-right:1px solid var(--line)}
  .topbar .cellruns{padding:11px 16px;text-align:center}
  .topbar .lbl{font-size:10px;letter-spacing:1.3px;text-transform:uppercase;color:var(--dim)}
  .topbar .nm{font-size:21px;font-weight:700;margin-top:1px}
  .topbar .nm .orig{font-size:14px;font-weight:400;color:var(--dim);margin-left:8px}
  .topbar .big{font-size:30px;font-weight:800;color:var(--acc);line-height:1.05}
  .topbar .sub2{font-size:11px;color:var(--dim)}
  .hdesc{color:#aeb7c4;font-size:13px;margin:10px 0 0;max-width:900px}

  .plan{background:linear-gradient(180deg,#1b1710,#14171c);border:1px solid #3a2f1c;
    border-radius:12px;padding:14px 16px;margin:14px 0 22px}
  .plan h3{margin:0 0 3px;font-size:15px;color:var(--acc)}
  .plan .sub{color:var(--dim);font-size:12px;margin-bottom:11px}
  .runs{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:10px}
  .run{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:10px 12px}
  .run .no{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:var(--dim)}
  .run .cfg{font-size:12.5px;font-weight:600;margin:2px 0 7px}
  .run ul{margin:6px 0 0;padding-left:15px} .run li{font-size:11.5px;color:var(--dim);margin:1px 0}
  .run .cats{display:flex;flex-wrap:wrap;gap:4px;margin:2px 0 4px}
  .chipcat{font-size:10px;padding:1px 6px;border-radius:9px;border:1px solid var(--line);color:var(--dim)}
  .chipcat.pc-ladder{color:#8ab4f8;border-color:#24384f}
  .chipcat.pc-run_cond{color:#f0a020;border-color:#4a3a20}
  .chipcat.pc-objective{color:#7fd1a0;border-color:#244634}
  .chipcat.pc-loadout{color:#d8a0f0;border-color:#3d2f52}
  .chipcat.pc-crew{color:#c9a0f0;border-color:#4a3060}
  .chipcat.plus{color:#6fb3c9;border-color:#234049}

  .sect{font-size:12px;text-transform:uppercase;letter-spacing:1.2px;color:var(--dim);
    margin:22px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
  .sect.small{font-size:11px;margin:14px 0 8px}
  .sect.shared{color:var(--acc);border-bottom-color:#4a3a20}
  .sect.lobby{color:#7f8b9c;border-bottom-color:#39404b}
  .sect.ladder{color:#8ab4f8;border-bottom-color:#24384f}
  .vnote{color:var(--dim);font-size:12px;margin:10px 0 0;max-width:880px}

  .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px}
  .card{position:relative;display:flex;gap:10px;background:var(--card);border:1px solid var(--line);
    border-radius:10px;padding:10px;align-items:flex-start}
  .card.done{background:#111a15;border-color:#2f5138;box-shadow:inset 3px 0 0 var(--ok)}
  .card.done .nm{text-decoration:line-through;color:#86c496}
  .card.done .cond,.card.done .conden{color:#6d8877}
  .card img{width:52px;height:52px;border-radius:6px;background:#0f1216;flex-shrink:0;object-fit:cover}
  .card .body{flex:1;min-width:0}
  .card .nm{font-weight:600;font-size:13.5px;display:flex;gap:7px;align-items:baseline;flex-wrap:wrap}
  .card .nm .orig{color:var(--dim);font-weight:400;font-size:11.5px}
  .card .cond{color:#9aa4b2;font-size:12px;margin-top:3px}
  .card .conden{color:#6d7684;font-size:11.5px;margin-top:2px}
  .badges{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}
  .b{font-size:10.5px;padding:1px 6px;border-radius:4px;border:1px solid var(--line);color:var(--dim)}
  .b.rw{color:var(--ok);border-color:#22402a} .b.dep{color:var(--acc2);border-color:#4a2626}
  .b.crew{color:var(--purple);border-color:#6b4fa0;background:#1c1526} .b.lob{color:var(--dim);border-color:#3a414c}
  .b.ex{color:#e0a3a0;border-color:#4a2e2c} .b.day{color:var(--blue);border-color:#24384f}
  .b.fit{color:#9fdfb0;border-color:#2f5138}
  .b.pc-ladder{color:#8ab4f8;border-color:#24384f}
  .b.pc-run_cond{color:#f0a020;border-color:#4a3a20}
  .b.pc-objective{color:#7fd1a0;border-color:#244634}
  .b.pc-loadout{color:#d8a0f0;border-color:#3d2f52}
  .b.pc-crew{color:#c9a0f0;border-color:#4a3060}
  .b.pc-farmable{color:#6fb3c9;border-color:#234049}
  .b.pc-meta{color:#9aa4b2;border-color:#333a44}
  .dep{font-size:11.5px;color:var(--acc2);margin-top:6px;padding:5px 7px;background:#1d1414;
    border-left:2px solid var(--acc2);border-radius:0 5px 5px 0}
  .dep b{color:#ffb3aa}
  .dep.free-note{color:var(--dim);background:#171a1f;border-left-color:var(--line)}
  .chk{width:15px;height:15px;accent-color:var(--acc);cursor:pointer;flex-shrink:0;margin-top:2px}
  .chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
  .chip{font-size:12px;padding:4px 10px;border-radius:14px;border:1px solid var(--line);
    background:var(--panel);cursor:pointer;color:var(--dim);user-select:none}
  .chip.on{background:var(--acc);color:#12100c;border-color:var(--acc);font-weight:600}
  .chip-ladder{border-color:#24384f;color:#8ab4f8}
  .chip-run_cond{border-color:#4a3a20;color:#f0a020}
  .chip-objective{border-color:#244634;color:#7fd1a0}
  .chip-loadout{border-color:#3d2f52;color:#d8a0f0}
  .chip-crew{border-color:#4a3060;color:#c9a0f0}
  .chip-farmable{border-color:#234049;color:#6fb3c9}
  .chip-meta{border-color:#333a44;color:#9aa4b2}
  .catsec-ladder{border-bottom-color:#24384f}
  .catsec-run_cond{border-bottom-color:#4a3a20;color:#d8a860}
  .catsec-objective{border-bottom-color:#244634;color:#9ad8b4}
  .catsec-loadout{border-bottom-color:#3d2f52;color:#c4a0e0}
  .catsec-crew{border-bottom-color:#4a3060;color:#c9a0f0}
  .catsec-farmable{border-bottom-color:#234049;color:#8fc8dc}
  .catsec-meta{border-bottom-color:#333a44}
  .chip .n{opacity:.7;margin-left:4px}
  .vtabs{display:flex;gap:7px;flex-wrap:wrap;margin:14px 0 4px}
  .vtab{padding:7px 13px;border-radius:9px;border:1px solid var(--line);background:var(--card);
    cursor:pointer;font-size:13px;color:var(--dim);text-align:left}
  .vtab:hover{border-color:var(--acc)} .vtab.on{border-color:var(--acc);background:#241d10;color:var(--txt);font-weight:600}
  .vtab .en{display:block;font-size:10.5px;font-weight:400;color:var(--dim);margin-top:1px}
  .vtab.on .en{color:var(--acc)} .vtab .n{display:block;font-size:10.5px;color:var(--dim);margin-top:2px}
  .empty{color:var(--dim);padding:40px;text-align:center}
  #toast{position:fixed;right:16px;bottom:16px;background:#14251a;border:1px solid #2f5138;
    color:#9fdfb0;padding:10px 14px;border-radius:9px;font-size:13px;opacity:0;
    transition:opacity .3s;pointer-events:none;z-index:60}
  #toast.show{opacity:1}
  .goal{background:linear-gradient(180deg,#1b1710,#14171c);border:1px solid #3a2f1c;
    border-radius:12px;padding:14px 18px;margin:0 0 18px}
  .goal .top{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  .goal .lbl{font-size:10px;letter-spacing:1.3px;text-transform:uppercase;color:var(--dim)}
  .goal .nm{font-size:16px;font-weight:700;margin-top:2px}
  .goal .cn{font-size:42px;font-weight:800;color:var(--acc);line-height:1}
  .goal .cn small{font-size:18px;color:var(--dim);font-weight:600}
  .goal .track{flex:1;min-width:180px;height:9px;background:#0f1216;border-radius:5px;overflow:hidden;
    border:1px solid var(--line)}
  .goal .fill{height:100%;background:linear-gradient(90deg,#c47f10,var(--acc));border-radius:5px}
  .goal .pct{font-size:12px;color:var(--dim)}
  .goal .btns{display:flex;gap:6px}
  .goal.done .cn{color:var(--ok)}
  .goal.done{border-color:#2f5138}
  .goal.done .fill{background:var(--ok)}
  .pin{margin-top:6px;font-size:11px;padding:2px 8px;border-radius:11px;cursor:pointer;
    border:1px solid #3a2f1c;background:#1b1710;color:var(--acc)}
  .pin:hover{border-color:var(--acc)}
  /* ---- счётчик в стиле окна достижений Steam ---- */
  .cntcard{display:flex;gap:18px;align-items:center;background:#1b1e22;
    border:1px solid #2b2f34;border-radius:6px;padding:16px 18px;margin:0 0 14px}
  .cntcard .cico{width:92px;height:92px;flex:none;border:1px solid #3a3f45;background:#0e1013;
    display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:3px}
  .cntcard .cico img{width:100%;height:100%;object-fit:cover;display:block}
  .cntcard .cbody{flex:1;min-width:0}
  .cntcard .cnm{font-size:19px;font-weight:700;line-height:1.2;margin-bottom:6px}
  .cntcard .cnm .orig{display:block;font-size:12px;font-weight:400;color:var(--dim);margin-top:3px}
  .cntcard .cds{font-size:13px;color:#9aa0a6;line-height:1.45;margin-bottom:10px}
  .sbar{position:relative;display:flex;height:30px;background:#4b5157;border-radius:2px;
    overflow:hidden;align-items:center;justify-content:center}
  .sfill{position:absolute;left:0;top:0;bottom:0;background:#a4d007}
  .snum{position:relative;z-index:1;font-size:15px;font-weight:700;color:#e8eaed;
    letter-spacing:.3px;white-space:nowrap}
  .snum .cur{color:#e8eaed}
  .snum.over .cur{color:#1d2206}
  .cntcard.fin .sfill{background:#6fae2a}
  .cfoot{font-size:12px;color:#8b9298;margin-top:8px;display:flex;gap:14px;flex-wrap:wrap;
    align-items:center}
  .cfoot .left{color:#a4d007;font-weight:600}
  .cntcard .cbtns{display:flex;gap:6px;margin-top:11px;flex-wrap:wrap;align-items:center}
  .cntcard input.num{width:88px;padding:4px 7px;border-radius:6px;background:#0e1013;
    border:1px solid #3a3f45;color:var(--fg);font:inherit;font-size:12px}
  /* ---- сводка по прогрессу ---- */
  .psum{background:linear-gradient(180deg,#151a20,#12161b);border:1px solid var(--line);
    border-radius:12px;padding:16px 20px;margin:0 0 18px}
  .psum .ph{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:12px}
  .psum .pbig{font-size:34px;font-weight:800;line-height:1}
  .psum .pbig small{font-size:17px;color:var(--dim);font-weight:600}
  .psum .ptot{color:var(--dim);font-size:13px}
  .psum .ptrack{height:14px;background:#0f1216;border:1px solid var(--line);border-radius:7px;
    overflow:hidden;margin-bottom:12px}
  .psum .pfill{height:100%;background:linear-gradient(90deg,#8a6d10,var(--acc));border-radius:7px}
  .psum .pgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(178px,1fr));gap:9px}
  .psum .pcell{background:#11151a;border:1px solid var(--line);border-radius:9px;padding:9px 11px}
  .psum .pcell .k{font-size:11px;color:var(--dim)}
  .psum .pcell .v{font-size:17px;font-weight:700;margin-top:2px}
  .psum .pcell .m{font-size:11px;color:var(--dim);margin-top:2px}
  .ver{font-size:11px;color:var(--dim);letter-spacing:.4px}
  #updpanel{border-bottom:1px solid var(--line);background:#141821;padding:10px 22px}
  #updpanel .upd-body{font-size:13px;color:var(--fg);line-height:1.5}
  .upd-notes{display:block;color:var(--dim);font-size:12px;margin:5px 0}
  .upd-go{margin-top:7px;padding:6px 14px;border-radius:8px;border:1px solid var(--acc);
    background:#1b1710;color:var(--acc);font:inherit;font-size:12px;cursor:pointer}
  .upd-go:hover{background:var(--acc);color:#10131a}
  .upd-bar{height:7px;background:#0f1216;border:1px solid var(--line);border-radius:4px;
    overflow:hidden;margin-top:8px}
  .upd-bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#8a6d10,var(--acc));
    transition:width .2s}
  .hitem.goaltab{border-color:#3a2f1c;background:#1b1710}
  .hitem.goaltab.sel{border-color:var(--acc)}
  #bar{position:fixed;left:0;bottom:0;height:3px;background:var(--acc);transition:width .2s;z-index:50}
</style>
</head>
<body>
<header>
  <h1>PAYDAY 2 <small>трекер достижений</small></h1>
  <div class="stat">Хайстов: <b id="s-heist">0</b></div>
  <div class="stat">Достижений: <b id="s-ach">0</b></div>
  <div class="stat">Отмечено: <b id="s-done">0</b> / <span id="s-tot">0</span>
    <span id="s-pct" style="color:var(--acc);font-weight:700"></span></div>
  <div class="grow"></div>
  <span id="live" title="связь с игрой">офлайн</span>
  <span id="ver" class="ver" title="версия приложения"></span>
  <button id="btn-update">Обновление</button>
  <button id="btn-import">Импорт прогресса</button>
  <button id="btn-reset">Сбросить</button>
</header>

<div id="updpanel" hidden>
  <div id="upd-body" class="upd-body">Проверяю обновления…</div>
  <div id="upd-bar" class="upd-bar" hidden><i></i></div>
</div>

<div id="importbar">
  <input type="text" id="steam-url" size="52"
         placeholder="ссылка на профиль Steam: https://steamcommunity.com/profiles/7656119.../stats/218620/achievements">
  <button class="go" id="btn-steam">Загрузить из Steam</button>
  <button id="btn-auto" title="Следить за профилем, пока играешь">Автообновление: выкл</button>
  <span id="steam-when" class="msg"></span>
  <input type="text" id="file-path" size="34" placeholder="путь к файлу со списком (необязательно)">
  <button id="btn-file">Из файла</button>
  <button id="btn-verify">Проверить данные</button>
  <button id="btn-wipe" class="danger">Сбросить всё и удалить файл</button>
  <span class="msg" id="imp-msg"></span>
</div>

<div id="wrap">
  <div id="side">
    <div class="bar">
      <input type="search" id="q" placeholder="Поиск хайста…">
      <input type="search" id="qa" placeholder="Поиск достижения…">
    </div>
    <div id="achresults" hidden></div>
    <div id="heistlist"></div>
  </div>
  <div id="main"></div>
</div>
<div id="toast"></div>
<div id="bar"></div>

<script>
const KEY='pd2app.v1';
const APP_VERSION='__VERSION__';
const ACH=[__ACH__], HEISTS=[__HEISTS__], PARALLEL=__PARALLEL__, GLOBAL=__GLOBAL__;
const CLS=__CLS__, CPRIO=__CPRIO__, ROUTEMETA=__ROUTEMETA__;
let done=new Set();
let lang='ru', sel=null, chips=new Set(), query='', vsel={};
let GOAL=null;
let COUNTS={};
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cnt=ids=>ids.reduce((n,i)=>n+(done.has(i)?1:0),0);

function sortCards(ids,opts){
  opts=opts||{};
  return ids.slice().sort((x,y)=>{
    const a=ACH[x],b=ACH[y];
    const da=done.has(x)?1:0, db=done.has(y)?1:0;
    if(da!==db) return da-db;
    if(opts.cumulativeFirst){
      const ca=(a.c==='collect')?0:1, cb=(b.c==='collect')?0:1;
      if(ca!==cb) return ca-cb;
    }
    return (a.p??999)-(b.p??999);
  });
}

async function api(path,opts){
  const r=await fetch(path,Object.assign({headers:{'Content-Type':'application/json'}},opts||{}));
  return r.json();
}
function ago(ts){
  const s = Math.max(0, Math.round(Date.now()/1000 - ts));
  if (s < 60) return 'только что';
  if (s < 3600) return Math.round(s/60) + ' мин назад';
  return Math.round(s/3600) + ' ч назад';
}
function toast(msg,ms){
  const t=document.getElementById('toast');
  t.textContent=msg; t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'), ms||2600);
}
function msg(text,kind){
  const el=document.getElementById('imp-msg');
  el.textContent=text; el.className='msg'+(kind?' '+kind:'');
}
function updateStats(){
  document.getElementById('s-heist').textContent=HEISTS.length;
  document.getElementById('s-ach').textContent=ACH.length;
  document.getElementById('s-done').textContent=done.size;
  document.getElementById('s-tot').textContent=ACH.length;
  document.getElementById('s-pct').textContent=
    '('+(ACH.length?Math.round(done.size/ACH.length*1000)/10:0)+'%)';
  document.getElementById('bar').style.width=(done.size/ACH.length*100)+'%';
}

/* ---------------------------------------------------------------- sidebar */
function renderSide(){
  const q=query.trim().toLowerCase(), box=document.getElementById('heistlist');
  const groups={};
  for(const h of HEISTS){
    if(h.page==='Basics') continue;          // the tutorial heist has no achievements
    const ru=(h.name_ru||'').toLowerCase(), en=h.name.toLowerCase();
    if(q && !ru.includes(q) && !en.includes(q)) continue;
    (groups[h.contractor||'Прочее']=groups[h.contractor||'Прочее']||[]).push(h);
  }
  const order=['Bain','The Dentist','The Elephant','The Butcher','The Continental','Vlad','Locke','Hector','Slaughterhouse','Jiu Feng','Прочее'];
  let html='';
  // "Обучение" (Basics) held no achievements, so its slot became the goal tab
  const gdone=cnt(GLOBAL);
  html+=`<div class="hitem goaltab ${sel==='__goal__'?'sel':''}" data-p="__goal__">
    <div class="nm">🎯 Цель и прогресс</div>
    <div class="rn">${done.size}/${ACH.length}</div></div>`;
  for(const g of order){
    if(!groups[g])continue;
    groups[g].sort((a,b)=>(a.min_runs??0)-(b.min_runs??0)||b.ids.length-a.ids.length);
    html+=`<div class="grp">${esc(g)} (${groups[g].length})</div>`;
    for(const h of groups[g]){
      const t=h.ids.length,dn=cnt(h.ids),pct=t?Math.round(dn/t*100):0;
      const mp=h.mode==='stealth'?'<span class="pill st">тихий</span>':
               h.mode==='loud'?'<span class="pill ld">шумный</span>':'';
      html+=`<div class="hitem ${sel===h.page?'sel':''}" data-p="${esc(h.page)}">
        <div class="nm">${esc(lang==='ru'&&h.name_ru?h.name_ru:h.name)} ${mp}</div>
        <div class="rn ${(h.min_runs??0)>1?'many':''}">${h.min_runs??0}✦</div>
        <div class="bar-mini"><i style="width:${pct}%"></i></div>
        <div class="rn">${dn}/${t}</div></div>`;
    }
  }
  html+=`<div class="grp">Прочее</div>`;
  const g=cnt(GLOBAL);
  html+=`<div class="hitem ${sel==='__global__'?'sel':''}" data-p="__global__">
    <div class="nm">🏆 Общие и накопительные</div><div class="rn">${g}/${GLOBAL.length}</div></div>`;
  box.innerHTML=html;
  box.querySelectorAll('.hitem').forEach(el=>el.onclick=()=>{sel=el.dataset.p;renderSide();renderMain()});
}

/* ------------------------------------------------------------------ cards */
function cardHtml(i){
  const a=ACH[i], isDone=done.has(i);
  const ru=(lang==='ru'&&a.nr)?`<span class="orig">${esc(a.n)}</span>`:
           (lang==='en'&&a.nr)?`<span class="orig">${esc(a.nr)}</span>`:'';
  const cond=(lang==='ru'&&a.dr)?a.dr:a.d;
  const conden=(lang==='ru'&&a.dr)?a.d:'';
  const badges=[];
  if(a.fit==='extra')badges.push('<span class="b fit">можно дополнительно</span>');
  const PC={ladder:'Лестница сложности',run_cond:'Условие захода',objective:'Объект миссии',
            loadout:'Маска/снаряжение',crew:'Нужен полный состав',farmable:'Общий счётчик',
            meta:'Прогресс аккаунта'};
  if(a.pc&&PC[a.pc]) badges.push('<span class="b pc-'+a.pc+'">'+PC[a.pc]+'</span>');
  if(a.crew4)badges.push('<span class="b crew">нужен полный состав (4 игрока)</span>');
  if(a.tg) badges.push(`<span class="b">цель: ${a.tg}</span>`);
  if(a.sc==='lobby')badges.push('<span class="b lob">только лобби</span>');
  if(a.dy)badges.push(`<span class="b day">${a.dy}-й день</span>`);
  if(a.df.length)for(const d of a.df)badges.push(`<span class="b">${d}</span>`);
  if(a.p!=null)badges.push(`<span class="b">${a.p}%</span>`);
  const rw=a.r||{},rt=[];
  if(rw.masks)rt.push('маска: '+rw.masks.join(', '));
  if(rw.outfits)rt.push('костюм: '+rw.outfits.join(', '));
  if(rw.patterns)rt.push('рисунок: '+rw.patterns.join(', '));
  if(rw.materials)rt.push('материал: '+rw.materials.join(', '));
  if(rw.weapons)rt.push('оружие: '+rw.weapons.join(', '));
  if(rw.characters)rt.push('персонаж: '+rw.characters.join(', '));
  if(rw.other)rt.push('награда: '+rw.other.join(', '));
  if(rt.length)badges.push(`<span class="b rw">${esc(rt.join(' · '))}</span>`);
  let dep='';
  for(const d of (a.dp||[])){
    badges.push(`<span class="b dep">нужна маска ${esc(d.mask)}</span>`);
    if(d.kind==='dlc_set'&&d.unlocked_by&&d.unlocked_by.length)
      dep+=`<div class="dep">⚠ Нужны маски из набора <b>${esc(d.mask)}</b>. Их дают: <b>${d.unlocked_by.map(esc).join(', ')}</b>.</div>`;
    else if(d.kind==='unknown')
      dep+=`<div class="dep">⚠ Маска <b>${esc(d.mask)}</b> — вне списка достижений (ивент/сообщество/DLC).</div>`;
  }
  return `<div class="card ${isDone?'done':''}" data-i="${i}">
    <input class="chk" type="checkbox" ${isDone?'checked':''}>
    ${a.img?`<img src="${esc(a.img)}" alt="" loading="lazy">`:''}
    <div class="body">
      <div class="nm">${esc(lang==='ru'?(a.nr||a.n):a.n)}${ru}</div>
      <div class="cond">${esc(cond)}</div>
      ${conden?`<div class="conden">${esc(conden)}</div>`:''}
      ${badges.length?`<div class="badges">${badges.join('')}</div>`:''}
      ${dep}
      ${a.tg?`<button class="pin pinbtn" data-id="${a.i}">${(GOAL&&GOAL.id===a.i)?'★ закреплено':'Закрепить как цель'}</button>`:''}
    </div></div>`;
}

const PCNAME={ladder:'Лестница сложности',run_cond:'Условия захода',objective:'Объекты миссии',
  loadout:'Маски и снаряжение',crew:'Нужен полный состав',farmable:'Общие счётчики',meta:'Прогресс аккаунта'};
function groups(main,ids){
  if(!ids.length){main.insertAdjacentHTML('beforeend','<div class="empty">Нет достижений</div>');return}
  const byCat={},all={};
  for(const i of ids){const c=ACH[i].pc||'ladder';all[c]=(all[c]||0)+1;
    if(chips.size&&!chips.has(c))continue;(byCat[c]=byCat[c]||[]).push(i)}
  const ch=Object.entries(all).sort((x,y)=>y[1]-x[1]).map(([c,n])=>
    `<span class="chip chip-${c} ${chips.has(c)?'on':''}" data-c="${c}">${esc(PCNAME[c]||c)} <span class="n">${n}</span></span>`).join('');
  main.insertAdjacentHTML('beforeend',`<div class="chips">${ch}${chips.size?'<span class="chip" data-c="__clear">сбросить фильтр</span>':''}</div>`);
  main.querySelectorAll('.chip').forEach(el=>el.onclick=()=>{const c=el.dataset.c;
    if(c==='__clear')chips.clear();else chips.has(c)?chips.delete(c):chips.add(c);renderMain()});
  const ORDER=['ladder','run_cond','objective','loadout','crew','farmable','meta'];
  const keys=Object.keys(byCat).sort((a,b)=>ORDER.indexOf(a)-ORDER.indexOf(b));
  for(const c of keys){
    const list=sortCards(byCat[c]);
    main.insertAdjacentHTML('beforeend',
      `<div class="sect catsec-${c}">${esc(PCNAME[c]||c)} — ${list.length}</div><div class="cards">${list.map(cardHtml).join('')}</div>`);
  }
}

/* ------------------------------------------------------------------- main */
function goalPanel(){
  var g = GOAL;
  if(!g || g.id==null){ return ""; }
  var a = null;
  for(var i=0;i<ACH.length;i++) if(ACH[i].i===g.id) a=ACH[i];
  if(!a) return "";
  var tg = a.tg || 0;
  var cur = Math.min(g.count||0, tg);
  var pct = tg ? Math.round(cur/tg*100) : 0;
  var fin = tg && cur>=tg;
  return `<div class="goal ${fin?'done':''}">
    <div class="top">
      <div><div class="lbl">главная цель</div>
        <div class="nm">${esc(lang==='ru'?(a.nr||a.n):a.n)}</div></div>
      <div class="cn">${cur}<small> / ${tg}</small></div>
      <div class="track"><div class="fill" style="width:${pct}%"></div></div>
      <div class="pct">${pct}%${fin?' — закрыто':''}</div>
      <div class="btns">
        <button id="g-minus">−10</button>
        <button id="g-minus1">−1</button>
        <button id="g-plus1">+1</button>
        <button id="g-plus">+10</button>
        <button id="g-clear">Открепить</button>
      </div>
    </div>
    <div class="cond" style="margin-top:8px">${esc(lang==='ru'?(a.dr||a.d):a.d)}</div>
  </div>`;
}

/* ------------------------------------------- вкладка «Цель и прогресс» */
// Счётчик в стиле окна достижений Steam: иконка, название, условие, полоса
// с «151 / 666» и разбивкой «готово / осталось».
function cntCard(a, big){
  const tg=a.tg||0;
  // an earned achievement IS its counter at full -- the two can never disagree
  const earned=done.has(a.i);
  const cur=earned?tg:Math.min(COUNTS[String(a.i)]||0, tg);
  const pct=tg?Math.round(cur/tg*100):0, fin=tg&&cur>=tg;
  const left=Math.max(0,tg-cur);
  const nm=lang==='ru'?(a.nr||a.n):a.n;
  const nmEn=(lang==='ru'&&a.n)?`<span class="orig">${esc(a.n)}</span>`:'';
  const ds=lang==='ru'?(a.dr||a.d):a.d;
  const wide=big?'style="flex-direction:column;align-items:stretch"':'';
  return `<div class="cntcard ${fin?'fin':''}" data-i="${a.i}" ${wide}>
    ${a.img?`<div class="cico"><img src="${esc(a.img)}" alt="" loading="lazy"></div>`:''}
    <div class="cbody">
      <div class="cnm">${esc(nm)}${nmEn}</div>
      <div class="cds">${esc(ds)}</div>
      <div class="sbar">
        <div class="sfill" style="width:${pct}%"></div>
        <div class="snum ${pct>=50?'over':''}"><span class="cur">${cur}</span> / ${tg}</div>
      </div>
      <div class="cfoot">
        <span class="left">${pct}%</span>
        <span>${fin?'закрыто':`осталось ${left}`}</span>
        <span>${earned?'✓ отмечено':'не отмечено'}</span>
      </div>
      <div class="cbtns">
        <button class="cb" data-cb="-10">−10</button>
        <button class="cb" data-cb="-1">−1</button>
        <button class="cb" data-cb="1">+1</button>
        <button class="cb" data-cb="10">+10</button>
        <input class="num" type="number" min="0" step="1" value="${cur}" data-num="${a.i}">
        <button class="cset" data-set="${a.i}">ОК</button>
        <button class="cpin ${GOAL&&GOAL.id===a.i?'on':''}" data-pin="${a.i}">
          ${GOAL&&GOAL.id===a.i?'★ закреплено':'закрепить'}</button>
      </div>
    </div></div>`;
}

function progressSummary(){
  const total=ACH.length, dn=done.size, pct=total?Math.round(dn/total*1000)/10:0;
  const withTg=ACH.filter(a=>a.tg).length;
  const tgDone=ACH.filter(a=>a.tg&&done.has(a.i)).length;
  const noTg=total-withTg, noTgDone=ACH.filter(a=>!a.tg&&done.has(a.i)).length;
  const heists=HEISTS.length;
  const hDone=HEISTS.filter(h=>h.ids.length&&h.ids.every(i=>done.has(i))).length;
  const cells=[
    ['всего достижений', total, ''],
    ['отмечено', dn, pct+'% от всех'],
    ['со счётчиком', withTg, tgDone+' закрыто'],
    ['без счётчика', noTg, noTgDone+' закрыто'],
    ['хайстов пройдено', hDone+' / '+heists, ''],
  ];
  return `<div class="psum">
    <div class="ph">
      <div class="pbig">${dn}<small> / ${total}</small></div>
      <div class="ptot">достижений получено — ${pct}%</div>
      <div class="ptot">осталось ${total-dn}</div>
    </div>
    <div class="ptrack"><div class="pfill" style="width:${total?dn/total*100:0}%"></div></div>
    <div class="pgrid">${cells.map(c=>
      `<div class="pcell"><div class="k">${c[0]}</div><div class="v">${c[1]}</div>
       <div class="m">${c[2]||'&nbsp;'}</div></div>`).join('')}</div>
  </div>`;
}

function renderGoalTab(){
  const main=document.getElementById('main');
  const withTg=ACH.filter(a=>a.tg);
  const sorted=[...withTg].sort((a,b)=>{
    const pa=(COUNTS[String(a.i)]||0)/(a.tg||1), pb=(COUNTS[b.i]||0)/(b.tg||1);
    return pb-pa || b.tg-a.tg;
  });
  const goal=GOAL&&GOAL.id!=null?ACH.find(a=>a.i===GOAL.id):null;
  const rest=sorted.filter(a=>!goal||a.i!==goal.i);
  let html=`<div class="topbar">
    <div class="cellname"><div class="lbl">вкладка</div>
      <div class="nm">Цель и прогресс</div>
      <div class="sub2">счётчики и общая статистика</div></div>
    <div class="cellruns"><div class="lbl">готово</div>
      <div class="big">${Math.round(done.size/ACH.length*1000)/10}%</div></div></div>
    <div id="maininner"><div class="colmain">`;
  html+=progressSummary();
  html+=`<div class="sect">Закреплённая цель</div>`;
  html+= goal ? cntCard(goal,true)
    : `<div class="empty">Цель не закреплена. Нажми «закрепить» у любого достижения
       со счётчиком ниже — оно появится здесь крупным блоком.</div>`;
  if(goal) html+=`<div style="text-align:right;margin:-6px 0 18px">
    <button id="g-clear">Открепить</button></div>`;
  html+=`<div class="sect">Все счётчики — ${rest.length}</div>
    <p class="vnote">Число приходится ставить вручную: Steam отдаёт только факт
     получения достижения, но не промежуточный прогресс. Дойдёшь до цели — галочка
     встанет сама.</p>
    <div class="cards">${rest.map(a=>cntCard(a)).join('')}</div>`;
  html+=`</div><div class="colside">
    <div class="sect">Куда идёт счётчик</div>
    <p class="vnote">Счётчики считают всё подряд: убийства, собранные предметы,
     выстрелы. Их можно закрыть в любом хайсте, поэтому в плане захода они идут
     отдельной строкой «Общие счётчики».</p>
    <p class="vnote" id="goal-sync"></p>
  </div></div>`;
  main.innerHTML=html;
}

function renderMain(){
  const main=document.getElementById('main');
  if(sel==='__goal__'){ renderGoalTab(); return; }
  if(sel==='__global__'){
    const ladd=(ROUTEMETA&&ROUTEMETA.ladders)||[];
    const ladSet=new Set(ladd);
    // лестницы выведены в свою секцию — в общем списке их повторять нельзя,
    // иначе все 24 рисуются на странице дважды
    const inh=[...(PARALLEL.heist||[]),...(PARALLEL.anywhere||[])].filter(i=>!ladSet.has(i));
    const lob=PARALLEL.lobby||[];
    main.innerHTML=`<div class="topbar">
      <div class="cellname"><div class="lbl">список</div><div class="nm">Общие и накопительные</div>
      <div class="sub2">делаются в любом хайсте, кроме лобби</div></div>
      <div class="cellruns"><div class="lbl">всего</div><div class="big">${inh.length+lob.length+ladd.length}</div></div></div>
      <div id="maininner"><div class="colmain">
      <div class="sect">Делаются в хайсте — ${inh.length}</div>
      <div class="cards">${sortCards(inh,{cumulativeFirst:true}).map(cardHtml).join('')}</div>
      <div class="sect lobby">Только в лобби / убежище — ${lob.length}</div>
      <div class="cards">${sortCards(lob).map(cardHtml).join('')}</div>
      <div class="sect ladder">Лестницы контракторов — ${ladd.length}</div>
      <p class="vnote">Закрывается прохождением ВСЕХ контрактов на нужной сложности, а не
       одного хайста, поэтому вынесено отдельно.</p>
      <div class="cards">${sortCards(ladd).map(cardHtml).join('')}</div></div><div class="colside"></div></div>`;
    return;
  }
  const h=HEISTS.find(x=>x.page===sel);
  if(!h){main.innerHTML='<div class="empty">Выбери хайст слева</div>';return}
  let ids=h.ids, planSrc=h.plan||{}, activeVar=null;
  if(h.variants&&h.variants.length){
    if(vsel[sel]===undefined||!h.variants.some(v=>v.ru===vsel[sel])) vsel[sel]=h.variants[0].ru;
    activeVar=h.variants.find(v=>v.ru===vsel[sel]);
    if(activeVar){ids=activeVar.ids; if(activeVar.plan) planSrc=activeVar.plan}
  }
  const runs=(planSrc.runs||[]).length;
  const gearKills=h.ids.filter(i=>{
    const a=ACH[i],rw=a.r||{};
    return (rw.masks||rw.outfits||rw.patterns||rw.materials||rw.weapons||rw.characters||[]).length || a.c==='count';
  });
  const independent=[...(PARALLEL.heist||[]),...(PARALLEL.anywhere||[])];

  let html=`<div class="topbar">
    <div class="cellname"><div class="lbl">название</div>
      <div class="nm">${esc(lang==='ru'&&h.name_ru?h.name_ru:h.name)}${(h.name_ru&&h.name_ru!==h.name)?`<span class="orig">${esc(h.name)}</span>`:''}</div>
      <div class="sub2">${esc(h.contractor)} · ${h.mode==='stealth'?'тихий':h.mode==='loud'?'шумный':'любой режим'}${h.classic?' · классический':''}
        ${h.variant_packs&&h.variant_packs.length?' · набор: '+h.variant_packs.join(', '):''}
        ${h.wiki?` · <a href="${esc(h.wiki)}" target="_blank">вики ↗</a>`:''}</div></div>
    <div class="cellruns"><div class="lbl">кол-во проходов</div><div class="big">${runs}</div>
      <div class="sub2">${cnt(h.ids)}/${h.ids.length} отмечено</div></div></div>
  <div id="maininner"><div class="colmain">`;
  if(lang==='ru'&&h.desc_ru)html+=`<p class="hdesc">${esc(h.desc_ru)}</p>`;
  if(h.variants&&h.variants.length){
    const kt=h.variant_kind==='loot'?'Разновидности добычи':h.variant_kind==='day'?'Дни ограбления':'Разновидности карты';
    html+=`<div class="sect">${kt} — ${h.variants.length}</div>
      <div class="vtabs">${h.variants.map(v=>`<div class="vtab ${v.ru===vsel[sel]?'on':''}"
        data-v="${esc(v.ru)}">${esc(v.ru)}<span class="en">${esc(v.en)}</span>
        <span class="n">${v.ids.length} достижений</span></div>`).join('')}</div>
      <p class="vnote">${h.variant_kind==='loot'
        ? 'Разновидность выбирается при взятии контракта, и у каждой свой набор — на золоте ячейки не закрыть.'
        : h.variant_kind==='day'
        ? 'Контракт многоходовый: «на 2 день» берутся, только если ты доиграл до второго дня.'
        : 'У каждой карты свой набор, ничего не смешано.'}</p>`;
  }
  const pl=planSrc.runs||[];
  const PC2={ladder:'Лестница',run_cond:'Условия захода',objective:'Объекты',
             loadout:'Снаряжение',crew:'Четверо',farmable:'Счётчики',meta:'Аккаунт'};
  const globalFarm=(ROUTEMETA&&ROUTEMETA.global_farmable)||[];
  if(pl.length){
    const grind=(planSrc.grind||[]).map(g=>`<b>${esc(g.name)}</b> ×${g.times}`).join(', ');
    html+=`<div class="plan">
      <h3>Проходов для всех достижений: ${pl.length}${activeVar?' <span style="font-weight:400;color:var(--dim)">— «'+esc(activeVar.ru)+'»</span>':''}</h3>
      <div class="sub">Лестница сложностей закрывается одним проходом на максимуме. Всё, что несовместимо между собой — отдельный проход. Каждый проход заодно двигает <b>${globalFarm.length}</b> общих счётчиков.</div>
      <div class="runs">${pl.map((r,k)=>{
        const cats=Object.entries(r.by_cat||{}).sort((x,y)=>y[1]-x[1])
          .map(([c,n])=>`<span class="chipcat pc-${c}">${PC2[c]||c} ${n}</span>`).join('');
        return `<div class="run"><div class="no">Проход ${k+1}</div>
        <div class="cfg">${esc(r.label)}</div>
        <div class="cats">${cats}<span class="chipcat plus">+${globalFarm.length} общих</span></div>
        <ul>${r.ach.map(n=>`<li>${esc(n)}</li>`).join('')}</ul></div>`}).join('')}</div>
      ${grind?`<div class="grind">Отдельно требует повторов: ${grind}</div>`:''}</div>`;
  }
  html+=`<div class="sect">Достижения на этом ограблении — ${ids.length}${activeVar?' («'+esc(activeVar.ru)+'»)':''}</div>`;
  if(ids.length)html+=`<div class="cards">${sortCards(ids).map(cardHtml).join('')}</div>`;
  else html+=`<div class="empty">У этого хайста нет достижений</div>`;
  const others=(h.variants||[]).filter(v=>!activeVar||v.ru!==activeVar.ru);
  for(const v of others)
    html+=`<div class="sect small">${esc(v.ru)} (${esc(v.en)}) — ${v.ids.length}</div>
      <div class="cards">${sortCards(v.ids).map(cardHtml).join('')}</div>`;
  // Каждая карточка на странице ровно один раз: секции разновидностей забрали
  // свои id, хвост несёт только то, что ни одна секция не показала. Раньше
  // здесь лежал полный h.ids и «Транспорт» рисовал 59 карточек дважды.
  const shown=new Set(ids);
  for(const v of others) for(const i of v.ids) shown.add(i);
  const rest=h.ids.filter(i=>!shown.has(i));
  if(rest.length)
    html+=`<div class="sect">Остальные достижения хайста — ${rest.length}</div>
      <p class="vnote">Общие для всех разновидностей — не привязаны к одной карте
       или типу добычи, поэтому отдельно от списков выше.</p>
      <div class="cards">${sortCards(rest).map(cardHtml).join('')}</div>`;
  html+='</div><div class="colside">';
  // Полка наград осталась карточками — так он её просил обратно. Это осознанный
  // повтор: секция показывает подмножество списков слева как единый «стеллаж»,
  // массовые дубли (весь список хайста дважды) убраны выше.
  html+=`<div class="sect shared">Маски и убийства на этом хайсте — ${gearKills.length}</div>
    <p class="vnote">Награды за маски, снаряжение и счётчики убийств именно этого
     хайста. Они же входят в списки слева.</p>
    ${gearKills.length?`<div class="cards">${sortCards(gearKills).map(cardHtml).join('')}</div>`
                     :'<div class="empty">Нет таких достижений</div>'}`;
  const indepShown=independent.filter(i=>!h.ids.includes(i));
  html+=`<div class="sect">Независимые — можно делать когда угодно — ${indepShown.length}</div>
    <p class="vnote">Килы, сумки, навыки, репутация. Засчитываются в любом заходе.</p>
    <div class="cards">${sortCards(indepShown,{cumulativeFirst:true}).slice(0,60).map(cardHtml).join('')}</div>`;
  html+='</div></div>';
  main.innerHTML=html;
  main.querySelectorAll('.vtab').forEach(el=>el.onclick=()=>{vsel[sel]=el.dataset.v;renderMain()});
}

/* ------------------------------------------------------------- behaviour */
document.getElementById('main').addEventListener('change', async e=>{
  const c=e.target.closest('.card'); if(!c) return;
  const i=+c.dataset.i, want=e.target.checked;
  const r=await api('/api/toggle',{method:'POST',body:JSON.stringify({id:i,done:want})});
  done=new Set(r.done); updateStats(); renderSide(); renderMain();
});
const ares=document.getElementById('achresults');
function whereOf(i){
  for(const h of HEISTS){
    if(h.ids.includes(i)) return (lang==='ru'&&h.name_ru?h.name_ru:h.name);
    for(const v of (h.variants||[])) if(v.ids.includes(i))
      return (lang==='ru'&&h.name_ru?h.name_ru:h.name)+' → '+v.ru;
  }
  return (ACH[i].sc==='lobby')?'лобби / убежище':'общее, в любом хайсте';
}
function runAchSearch(){
  const q=document.getElementById('qa').value.trim().toLowerCase();
  const hl=document.getElementById('heistlist');
  if(q.length<2){ares.hidden=true;if(hl)hl.hidden=false;return}
  if(hl)hl.hidden=true;
  const hits=[];
  for(const a of ACH){
    const hay=(a.n+' '+(a.nr||'')+' '+a.d+' '+(a.dr||'')).toLowerCase();
    const at=hay.indexOf(q);
    if(at>=0)hits.push({a,at});
    if(hits.length>=120)break;
  }
  hits.sort((x,y)=>x.at-y.at);
  if(!hits.length){ares.innerHTML='<div class="grp">Ничего не найдено</div>';ares.hidden=false;return}
  ares.innerHTML='<div class="grp">Найдено: '+hits.length+'</div>'+hits.map(h=>{
    const a=h.a, nm=lang==='ru'?(a.nr||a.n):a.n;
    const ix=nm.toLowerCase().indexOf(q);
    const text=ix<0?esc(nm):esc(nm.slice(0,ix))+'<em>'+esc(nm.slice(ix,ix+q.length))+'</em>'+esc(nm.slice(ix+q.length));
    return `<button class="ares" data-i="${a.i}"><div class="an">${text}</div>
      <div class="aw">${esc(whereOf(a.i))}${a.p!=null?' · '+a.p+'%':''}</div>
      <div class="ac">${esc(lang==='ru'?(a.dr||a.d):a.d)}</div></button>`}).join('');
  ares.hidden=false;
  ares.querySelectorAll('.ares').forEach(b=>b.onclick=()=>{
    const i=+b.dataset.i;
    const host=HEISTS.find(h=>h.ids.includes(i))||HEISTS.find(h=>(h.variants||[]).some(v=>v.ids.includes(i)));
    ares.hidden=true;document.getElementById('heistlist').hidden=false;document.getElementById('qa').value='';
    sel=host?host.page:'__global__'; renderSide(); renderMain();
    const card=[...document.querySelectorAll('.card')].find(x=>+x.dataset.i===i);
    if(card){card.scrollIntoView({block:'center'});card.style.outline='2px solid var(--acc)';
      setTimeout(()=>card.style.outline='',2200);}
  });
}
async function bumpGoal(delta, value){
  const r=await api('/api/goal/bump',{method:'POST',
    body:JSON.stringify(delta!==undefined?{delta:delta}:{value:value})});
  GOAL=r;
  const p2=await api('/api/progress');
  done=new Set(p2.done); COUNTS=p2.counts||{}; updateStats(); renderSide(); renderMain();
}
async function bumpCount(id, delta, value){
  const r=await api('/api/count',{method:'POST',
    body:JSON.stringify(delta!==undefined?{id:id,delta:delta}:{id:id,value:value})});
  COUNTS=r.counts||{}; GOAL=r.goal||GOAL;
  const p2=await api('/api/progress');
  done=new Set(p2.done); updateStats(); renderSide(); renderMain();
  if(r.target&&r.count>=r.target) toast('Цель достигнута — achievement закрыт');
}
document.getElementById('main').addEventListener('click', async e=>{
  const b=e.target.closest('button');
  if(!b) return;
  const map={'g-plus':10,'g-plus1':1,'g-minus':-10,'g-minus1':-1};
  if(b.id in map) return bumpGoal(map[b.id]);
  if(b.classList.contains('cb'))
    return bumpCount(+b.closest('.cntcard').dataset.i, +b.dataset.cb);
  if(b.classList.contains('cset')){
    const id=+b.dataset.set;
    const inp=document.querySelector(`.cntcard[data-i="${id}"] input.num`);
    return bumpCount(id, undefined, Math.max(0, parseInt(inp&&inp.value,10)||0));
  }
  if(b.classList.contains('cpin')){
    const id=+b.dataset.pin;
    GOAL=await api('/api/goal',{method:'POST',body:JSON.stringify({id:id,count:0})});
    const p2=await api('/api/progress'); COUNTS=p2.counts||{};
    renderSide(); renderMain();
    toast(GOAL&&GOAL.id===id?'Цель закреплена — смотри во вкладке «Цель и прогресс»':'Закреплено');
    return;
  }
  if(b.id==='g-clear'){
    GOAL=await api('/api/goal',{method:'POST',body:JSON.stringify({id:null})});
    renderMain(); toast('Цель откреплена');
  }
  const pin=e.target.closest('.pinbtn');
  if(pin){
    const id=+pin.dataset.id;
    GOAL=await api('/api/goal',{method:'POST',body:JSON.stringify({id:id,count:0})});
    const p2=await api('/api/progress'); COUNTS=p2.counts||{};
    sel='__goal__'; renderSide(); renderMain();
    toast('Цель закреплена — открыта вкладка «Цель и прогресс»');
  }
});
document.getElementById('q').oninput=e=>{query=e.target.value;ares.hidden=true;
  document.getElementById('heistlist').hidden=false;renderSide()};
document.getElementById('qa').oninput=runAchSearch;
document.getElementById('qa').addEventListener('keydown',e=>{if(e.key==='Escape'){
  e.target.value='';ares.hidden=true;document.getElementById('heistlist').hidden=false}});
document.getElementById('btn-update').onclick=toggleUpdatePanel;
document.getElementById('btn-reset').onclick=async()=>{
  if(!confirm('Сбросить все отметки?'))return;
  const r=await api('/api/reset',{method:'POST',body:'{}'});
  done=new Set(r.done);updateStats();renderSide();renderMain();
};
document.getElementById('btn-import').onclick=()=>{
  const b=document.getElementById('importbar'); b.classList.toggle('show');
  document.getElementById('btn-import').classList.toggle('on', b.classList.contains('show'));
};
document.getElementById('btn-steam').onclick=async()=>{
  msg('Загружаю со Steam…');
  const r=await api('/api/import/steam',{method:'POST',
    body:JSON.stringify({url:document.getElementById('steam-url').value})});
  if(r.error){msg(r.error,'err');return}
  done=new Set(r.done);updateStats();renderSide();renderMain();
  msg('Готово: '+r.imported+' в Steam, добавлено '+r.added+(r.unknown&&r.unknown.length?',' +r.unknown.length+' не распознано':''),'ok');
  toast('Загружено '+r.added+' достижений');
};
document.getElementById('btn-file').onclick=async()=>{
  msg('Читаю файл…');
  const r=await api('/api/import/file',{method:'POST',
    body:JSON.stringify({path:document.getElementById('file-path').value})});
  if(r.error){msg(r.error,'err');return}
  done=new Set(r.done);updateStats();renderSide();renderMain();
  msg('Распознано '+r.imported+', добавлено '+r.added+
      (r.unknown&&r.unknown.length?',' +r.unknown.length+' не распознано':''),'ok');
};
document.getElementById('btn-verify').onclick=async()=>{
  msg('Проверяю…');
  const r=await api('/api/verify',{method:'POST',body:'{}'});
  if(r.error){msg(r.error,'err');return}
  const f=r.facts||{};
  msg('Итог: '+f.total+' достижений, отмечено '+f.progress+' ('+f.progress_pct+
      '%), не учтено '+f.unaccounted+
      '. Ошибок: '+r.problems.length+', предупреждений: '+r.warnings.length,
      r.ok?'ok':'err');
  toast('Ошибок данных: '+r.problems.length);
};
document.getElementById('btn-wipe').onclick=async()=>{
  if(!confirm('Удалить все отметки и сам файл прогресса?\nПотом можно будет загрузить заново.'))return;
  const r=await api('/api/reset',{method:'POST',body:JSON.stringify({wipe:true})});
  done=new Set(r.done);updateStats();renderSide();renderMain();
  msg('Очищено '+r.cleared+' отметок, файл удалён. Можно загружать заново.','ok');
  toast('Прогресс сброшен');
};

/* ------------------------------------------------------------ live feed */
function connect(){
  const es=new EventSource('/api/events');
  const dot=document.getElementById('live');
  es.onopen=()=>{dot.textContent='на связи';dot.classList.add('on')};
  es.onerror=()=>{dot.textContent='офлайн';dot.classList.remove('on')};
  es.addEventListener('progress', async ev=>{
    const r=await api('/api/progress');
    done=new Set(r.done);updateStats(); COUNTS=r.counts||{};
    if(r.goal&&r.goal.id!=null) GOAL=r.goal;
    const n=(JSON.parse(ev.data).added||[]).length;
    if(n) toast('Новых достижений: '+n);
    renderSide();
    const card=[...document.querySelectorAll('.card')];
    if(card.length) renderMain();
  });
  es.addEventListener('goal', async ev=>{
    const r=await api('/api/progress');
    GOAL=(r.goal&&r.goal.id!=null)?r.goal:null; COUNTS=r.counts||{};
    renderSide(); renderMain();
  });
  es.addEventListener('update', ev=>{
    const u=JSON.parse(ev.data);
    const bar=document.getElementById('upd-bar'), fill=bar&&bar.querySelector('i');
    const body=document.getElementById('upd-body');
    if(!body) return;
    if(u.stage==='downloading'){
      bar.hidden=false;
      fill.style.width=(u.pct||0)+'%';
      body.textContent='Скачиваю обновление… '+Math.round(u.pct||0)+'%';
    } else if(u.stage==='swapping'){
      body.textContent='Устанавливаю — заменяю файл приложения…';
    } else if(u.stage==='restarting'){
      bar.hidden=true;
      body.innerHTML='<b>Обновлено до v'+esc(u.version||'')+
        ' — приложение перезапускается.</b> Откроется новое окно.';
    } else if(u.stage==='error'){
      bar.hidden=true;
      body.innerHTML='<span style="color:var(--bad)">Ошибка обновления: '+esc(u.error||'')+'</span>';
    }
  });
}

/* ------------------------------------------------------- обновление */
let updBusy=false;
function updShow(html){
  document.getElementById('updpanel').hidden=false;
  document.getElementById('upd-body').innerHTML=html;
}
async function toggleUpdatePanel(){
  if(updBusy) return;
  const p=document.getElementById('updpanel');
  if(!p.hidden){ p.hidden=true; return; }
  updShow('Проверяю обновления…');
  let r;
  try { r=await api('/api/update/check'); }
  catch(e){ updShow('Сервер обновлений недоступен.'); return; }
  if(r.error){ updShow('<span style="color:var(--bad)">'+esc(r.error)+'</span>'); return; }
  if(!r.latest){
    updShow('Установлена v'+esc(r.current)+
      '. На GitHub ещё нет ни одного релиза — обновляться не с чего.');
    return;
  }
  if(!r.has_update){
    updShow('<b>У тебя последняя версия v'+esc(r.current)+'</b>'+
      ' — на GitHub v'+esc(r.latest)+'. ✓');
    return;
  }
  updShow('<b>Доступна v'+esc(r.latest)+'</b> — установлена v'+esc(r.current)+
    '.<br><span class="upd-notes">'+esc((r.notes||'').slice(0,400))+'</span><br>'+
    '<button class="upd-go" onclick="runUpdate()">Скачать и установить</button>');
}
async function runUpdate(){
  if(updBusy) return;
  updBusy=true;
  const body=document.getElementById('upd-body');
  body.textContent='Скачиваю обновление…';
  try { await api('/api/update/install',{method:'POST',body:'{}'}); }
  catch(e){ body.innerHTML='<span style="color:var(--bad)">Не удалось запустить обновление.</span>'; updBusy=false; }
}


(async function boot(){
  const [data,prog]=await Promise.all([api('/api/data'),api('/api/progress')]);
  ACH.length=0; data.achievements.forEach(a=>ACH.push(a));
  HEISTS.length=0; data.heists.forEach(h=>HEISTS.push(h));
  done=new Set(prog.done);
  GOAL=(prog.goal&&prog.goal.id!=null)?prog.goal:null;
  COUNTS=prog.counts||{};
  renderSide(); updateStats();
  const ve=document.getElementById('ver');
  if(ve) ve.textContent='v'+APP_VERSION;
  sel='GO Bank'; renderSide(); renderMain();
  connect();
})();
</script>
</body></html>
"""


def build():
    ui = UI

    def js(obj):
        """JSON safe to inline inside a <script> block."""
        s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        # only the *payload* must be neutralised -- escaping the document's own
        # closing </script> leaves the tag unclosed and the script never runs
        return s.replace("</script>", "<\\/script>").replace("<!--", "<\\!--")

    ui = ui.replace("__ACH__", js(PAYLOAD["achievements"]))
    ui = ui.replace("__HEISTS__", js(PAYLOAD["heists"]))
    ui = ui.replace("__PARALLEL__", js(PAYLOAD["parallel"]))
    ui = ui.replace("__GLOBAL__", js(PAYLOAD["global_ids"]))
    ui = ui.replace("__CLS__", js(PAYLOAD["category_labels"]))
    ui = ui.replace("__CPRIO__", js(PAYLOAD["category_priority"]))
    ui = ui.replace("__ROUTEMETA__", js(PAYLOAD.get("route_meta") or {}))
    ui = ui.replace("__VERSION__", version.VERSION)

    if ui.count("</script>") != 1:
        raise SystemExit("в шаблоне ожидался ровно один </script>, найдено %d"
                         % ui.count("</script>"))

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "ui.html"), "w", encoding="utf-8") as f:
        f.write(ui)
    import shutil
    shutil.copy(SRC, os.path.join(HERE, "data", "app_data.json"))
    # the API needs the icons too, otherwise the app shows bare cards
    with open(os.path.join(HERE, "data", "steam_images.json"), "w",
              encoding="utf-8") as _f:
        json.dump({n: s.get("img", "") for n, s in steam.items()}, _f,
                  ensure_ascii=False)
    shutil.copy(os.path.join(os.path.dirname(HERE), "data", "ru_linked.json"),
                os.path.join(HERE, "data", "ru_linked.json"))
    # A real newline inside a JS string literal kills the whole script and the
    # page comes up blank with no visible error -- so actually parse it.
    _s = ui.find("<script>") + len("<script>")
    _e = ui.rfind("</script>")
    _tmp = os.path.join(HERE, "_syntax_check.js")
    with open(_tmp, "w", encoding="utf-8") as _f:
        _f.write(ui[_s:_e])
    try:
        _r = subprocess.run(["node", "--check", _tmp],
                            capture_output=True, text=True, timeout=60)
        if _r.returncode != 0:
            raise SystemExit("JS не проходит проверку синтаксиса:\n" + _r.stderr[:900])
    except FileNotFoundError:
        print("  (node не найден -- проверка синтаксиса JS пропущена)")
    finally:
        if os.path.exists(_tmp):
            os.remove(_tmp)

    print("ui.html:", len(ui) // 1024, "KB")


if __name__ == "__main__":
    build()