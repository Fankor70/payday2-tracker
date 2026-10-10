# -*- coding: utf-8 -*-
"""Render the single-file tracker: card grid + minimum-run planner."""
import json, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

data = json.load(open("payday/data/app_final.json", encoding="utf-8"))
steam = {a["name"]: a for a in json.load(open("payday/data/steam_parsed.json", encoding="utf-8"))}

slim = []
for a in data["achievements"]:
    s = steam.get(a["name"], {})
    slim.append({
        "i": a["id"], "n": a["name"],
        "nr": a.get("name_ru"), "d": a["desc"], "dr": a.get("desc_ru"),
        "p": a.get("pct"), "img": s.get("img", ""),
        "h": a["heists"], "df": a["difficulties"], "r": a.get("rewards") or {},
        "c": a["category"], "dp": a.get("deps") or [], "sc": a.get("scope"),
        "ex": a.get("exact"), "dy": a.get("day"), "dys": a.get("days"),
    })
data["achievements"] = slim
data["done"] = data.get("done_ids") or []
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
print("payload:", len(payload) // 1024, "KB")

HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PAYDAY 2 — Трекер достижений</title>
<style>
  :root{
    --bg:#0b0d10; --panel:#14171c; --panel2:#1a1e25; --line:#272d36;
    --txt:#e8ebf0; --dim:#8a94a3; --acc:#f0a020; --acc2:#e2574c;
    --ok:#3fb950; --blue:#58a6ff; --purple:#a371f7; --card:#161a20;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--txt);font:14px/1.5 "Segoe UI",Roboto,Arial,sans-serif;
       display:flex;flex-direction:column}
  a{color:var(--blue)}
  header{background:linear-gradient(90deg,#1c1510,#14171c);border-bottom:1px solid var(--line);
    padding:9px 16px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;
    position:sticky;top:0;z-index:20}
  header h1{font-size:15px;margin:0;letter-spacing:.4px;color:var(--acc)}
  header h1 small{color:var(--dim);font-weight:400;margin-left:7px;font-size:12px}
  .stat{font-size:12px;color:var(--dim)} .stat b{color:var(--txt);font-size:14px}
  .grow{flex:1}
  button,input[type=search]{background:var(--panel2);color:var(--txt);border:1px solid var(--line);
    border-radius:6px;padding:6px 10px;font:inherit;font-size:13px;cursor:pointer}
  button:hover{border-color:var(--acc)} button.on{background:var(--acc);color:#12100c;font-weight:600}
  input[type=search]{cursor:text;min-width:190px}

  #wrap{flex:1;display:flex;min-height:0}
  #side{width:320px;flex-shrink:0;border-right:1px solid var(--line);background:var(--panel);
    display:flex;flex-direction:column;min-height:0;position:relative}
  #side .bar{padding:9px;border-bottom:1px solid var(--line);display:grid;
    grid-template-columns:1fr;gap:6px;overflow:hidden}
  #side .bar input{width:100%;box-sizing:border-box}
  #heistlist{overflow-y:auto;flex:1;padding-bottom:40px}
  #achresults{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;padding:6px 0 40px}
  #achresults *{min-width:0;max-width:100%}
  .ares{display:block;width:100%;max-width:100%;box-sizing:border-box;text-align:left;background:none;
    border:0;border-bottom:1px solid var(--line);border-radius:0;padding:8px 12px;cursor:pointer;
    color:var(--txt);overflow:hidden;overflow-wrap:anywhere;word-break:break-word}
  .ares:hover{background:var(--panel2)}
  .ares .an{font-size:13px;font-weight:600;overflow-wrap:anywhere}
  .ares .an em{color:var(--acc);font-style:normal}
  .ares .aw{font-size:11px;color:var(--dim);margin-top:2px;overflow:hidden;
    text-overflow:ellipsis;white-space:nowrap}
  .ares .ac{font-size:11.5px;color:var(--dim);margin-top:1px;overflow-wrap:anywhere;
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .ares .none{color:var(--dim);font-size:10.5px}
  .grp{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--dim);
    padding:11px 12px 4px;font-weight:700}
  .hitem{display:flex;align-items:center;gap:7px;padding:6px 12px;cursor:pointer;
    border-left:3px solid transparent}
  .hitem:hover{background:var(--panel2)} .hitem.sel{background:#232932;border-left-color:var(--acc)}
  .hitem .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}
  .hitem .rn{font-size:10.5px;padding:1px 6px;border-radius:9px;border:1px solid var(--line);
    color:var(--dim);font-variant-numeric:tabular-nums;flex-shrink:0}
  .hitem .rn.many{color:var(--acc2);border-color:#4a2626}
  .bar-mini{height:3px;background:var(--line);border-radius:2px;width:38px;overflow:hidden;flex-shrink:0}
  .bar-mini i{display:block;height:100%;background:var(--ok)}
  .pill{font-size:10px;padding:0 5px;border-radius:8px;border:1px solid var(--line);color:var(--dim)}
  .pill.st{color:var(--blue)} .pill.ld{color:var(--acc2)}

  #main{flex:1;overflow-y:auto;padding:0;min-width:0;display:flex;flex-direction:column}
  #maininner{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:0;flex:1;min-height:0}
  @media (max-width:1200px){#maininner{grid-template-columns:minmax(0,1fr)}}
  .colmain{overflow-y:auto;padding:16px 20px 90px;min-width:0}
  .colside{overflow-y:auto;padding:16px 14px 90px;min-width:0;
    border-left:1px solid var(--line);background:#0f1216}
  @media (max-width:1200px){.colside{border-left:0;border-top:1px solid var(--line)}}
  .topbar{display:grid;grid-template-columns:1fr 210px;border-bottom:1px solid var(--line);
    background:linear-gradient(90deg,#1c1510,#14171c)}
  .topbar .cellname{padding:11px 20px;border-right:1px solid var(--line)}
  .topbar .cellruns{padding:11px 16px;text-align:center}
  .topbar .lbl{font-size:10px;letter-spacing:1.3px;text-transform:uppercase;color:var(--dim)}
  .topbar .nm{font-size:21px;font-weight:700;color:var(--txt);margin-top:1px}
  .topbar .nm .orig{font-size:14px;font-weight:400;color:var(--dim);margin-left:8px}
  .topbar .big{font-size:30px;font-weight:800;color:var(--acc);line-height:1.05}
  .topbar .sub2{font-size:11px;color:var(--dim)}
  .empty{color:var(--dim);padding:50px;text-align:center}

  .hhead{display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:4px}
  .hhead h2{margin:0;font-size:24px}
  .hhead h2 .orig{color:var(--dim);font-size:15px;font-weight:400;margin-left:9px}
  .hhead .meta{color:var(--dim);font-size:12px;margin-top:5px}
  .hdesc{color:#aeb7c4;font-size:13px;margin:10px 0 0;max-width:900px}

  .plan{background:linear-gradient(180deg,#1b1710,#14171c);border:1px solid #3a2f1c;
    border-radius:12px;padding:14px 16px;margin:16px 0 22px}
  .plan h3{margin:0 0 3px;font-size:15px;color:var(--acc)}
  .plan .sub{color:var(--dim);font-size:12px;margin-bottom:11px}
  .runs{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:10px}
  .run{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:10px 12px}
  .run .no{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:var(--dim)}
  .run .cfg{color:var(--txt);font-size:12.5px;font-weight:600;margin:2px 0 7px}
  .run ul{margin:0;padding-left:15px}
  .run li{font-size:11.5px;color:var(--dim);margin:1px 0}
  .grind{margin-top:10px;font-size:12px;color:var(--acc2)}
  .grind b{color:#ffb3aa}

  .sect{font-size:12px;text-transform:uppercase;letter-spacing:1.2px;color:var(--dim);
    margin:22px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}

  .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px}
  .card{display:flex;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:10px;
    padding:10px;align-items:flex-start}
  .card{position:relative}
  .card.done{opacity:1;background:#111a15;border-color:#2f5138;box-shadow:inset 3px 0 0 var(--ok)}
  .card.done .nm{text-decoration:line-through;color:#86c496}
  .card.done .cond,.card.done .conden{color:#6d8877}
  .card.done .chk{accent-color:var(--ok)}
  .card img{width:52px;height:52px;border-radius:6px;background:#0f1216;flex-shrink:0;object-fit:cover}
  .card .body{flex:1;min-width:0}
  .card .nm{font-weight:600;font-size:13.5px;cursor:pointer;display:flex;gap:7px;align-items:baseline}
  .card .nm .orig{color:var(--dim);font-weight:400;font-size:11.5px}
  .card .cond{color:#9aa4b2;font-size:12px;margin-top:3px}
  .card .conden{color:#6d7684;font-size:11.5px;margin-top:2px}
  .badges{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}
  .b{font-size:10.5px;padding:1px 6px;border-radius:4px;border:1px solid var(--line);color:var(--dim)}
  .b.rw{color:var(--ok);border-color:#22402a} .b.dep{color:var(--acc2);border-color:#4a2626}
  .b.crew{color:var(--purple);border-color:#3d2f52}
  .b.lob{color:var(--dim);border-color:#3a414c}
  .b.ex{color:#e0a3a0;border-color:#4a2e2c}
  .b.day{color:var(--blue);border-color:#24384f}
  .sect.lobby{color:#7f8b9c;border-bottom-color:#39404b}
  .sect.shared{color:var(--acc);border-bottom-color:#4a3a20}
  .sect.small{font-size:11px;color:#8a94a3;margin:14px 0 8px}
  .dep{font-size:11.5px;color:var(--acc2);margin-top:6px;padding:5px 7px;background:#1d1414;
    border-left:2px solid var(--acc2);border-radius:0 5px 5px 0}
  .dep b{color:#ffb3aa}
  .chk{width:15px;height:15px;accent-color:var(--acc);cursor:pointer;flex-shrink:0;margin-top:2px}
  .chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
  .chip{font-size:12px;padding:4px 10px;border-radius:14px;border:1px solid var(--line);
    background:var(--panel);cursor:pointer;color:var(--dim);user-select:none}
  .chip.on{background:var(--acc);color:#12100c;border-color:var(--acc);font-weight:600}
  .chip .n{opacity:.7;margin-left:4px}
  .vtabs{display:flex;gap:7px;flex-wrap:wrap;margin:14px 0 4px}
  .vtab{padding:7px 13px;border-radius:9px;border:1px solid var(--line);background:var(--card);
    cursor:pointer;font-size:13px;color:var(--dim);text-align:left}
  .vtab:hover{border-color:var(--acc)}
  .vtab.on{border-color:var(--acc);background:#241d10;color:var(--txt);font-weight:600}
  .vtab .en{display:block;font-size:10.5px;font-weight:400;color:var(--dim);margin-top:1px}
  .vtab.on .en{color:var(--acc)}
  .vtab .n{display:block;font-size:10.5px;color:var(--dim);margin-top:2px}
  .vnote{color:var(--dim);font-size:12px;margin:10px 0 0;max-width:880px}
  #bar{position:fixed;left:0;bottom:0;height:3px;background:var(--acc);transition:width .2s;z-index:50}
</style>
</head>
<body>
<header>
  <h1>PAYDAY 2 <small>трекер достижений</small></h1>
  <div class="stat">Хайстов: <b id="s-heist">0</b></div>
  <div class="stat">Достижений: <b id="s-ach">0</b></div>
  <div class="stat">Отмечено: <b id="s-done">0</b></div>
  <div class="stat" id="s-steam">из Steam: <b id="s-steamd">0</b></div>
  <div class="grow"></div>
  <button id="btn-lang" class="on">RU</button>
  <button id="btn-steam" title="Вернуть отметки из профиля Steam">Из Steam</button>
  <button id="btn-reset">Сбросить</button>
</header>
<div id="wrap">
  <div id="side">
    <div class="bar">
      <input type="search" id="q" placeholder="Поиск хайста…" autocomplete="off">
      <input type="search" id="qa" placeholder="Поиск достижения…" autocomplete="off">
    </div>
    <div id="achresults" hidden></div>
    <div id="heistlist"></div>
  </div>
  <div id="main"><div class="empty">Выбери хайст слева</div></div>
</div>
<div id="bar"></div>
<script id="data" type="application/json">__PAYLOAD__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const ACH = D.achievements, HEISTS = D.heists;
const KEY='pd2ach.v2';
let saved=[]; try{saved=JSON.parse(localStorage.getItem(KEY)||'[]')}catch(e){}
// first run: seed from the Steam profile snapshot the pipeline pulled
let done=new Set((saved&&saved.length)?saved:(D.done||[]));
let fromSteam=(D.done||[]).length;
let lang='ru', sel=null, chips=new Set(), query=''; const vsel={};
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const save=()=>localStorage.setItem(KEY,JSON.stringify([...done]));
const nameOf=h=>(lang==='ru'&&h.name_ru)?h.name_ru:h.name;
const cnt=ids=>ids.reduce((n,i)=>n+(done.has(i)?1:0),0);

function renderSide(){
  const q=query.trim().toLowerCase(), box=document.getElementById('heistlist');
  const groups={};
  for(const h of HEISTS){
    const ru=(h.name_ru||'').toLowerCase(), en=h.name.toLowerCase();
    if(q && !ru.includes(q) && !en.includes(q)) continue;
    (groups[h.contractor||'Прочее']=groups[h.contractor||'Прочее']||[]).push(h);
  }
  const order=['Bain','The Dentist','The Elephant','The Butcher','The Continental','Vlad','Locke',
               'Hector','Slaughterhouse','Jiu Feng','Прочее'];
  let html='';
  for(const g of order){
    if(!groups[g])continue;
    groups[g].sort((a,b)=>a.min_runs-b.min_runs||b.ids.length-a.ids.length);
    html+=`<div class="grp">${esc(g)} (${groups[g].length})</div>`;
    for(const h of groups[g]){
      const t=h.ids.length,d=cnt(h.ids),pct=t?Math.round(d/t*100):0;
      const mp=h.mode==='stealth'?'<span class="pill st">тихий</span>':
               h.mode==='loud'?'<span class="pill ld">шумный</span>':'';
      html+=`<div class="hitem ${sel===h.page?'sel':''}" data-p="${esc(h.page)}">
        <div class="nm">${esc(lang==='ru'&&h.name_ru?h.name_ru:h.name)} ${mp}</div>
        <div class="rn ${h.min_runs>1?'many':''}" title="минимум заходов">${h.min_runs?h.min_runs+'✦':'—'}</div>
        <div class="bar-mini"><i style="width:${pct}%"></i></div>
        <div class="rn">${d}/${t}</div></div>`;
    }
  }
  html+=`<div class="grp">Прочее</div>`;
  const g=cnt(D.global_ids);
  html+=`<div class="hitem" data-p="__global__"><div class="nm">🏆 Общие и накопительные</div>
    <div class="rn">${g}/${D.global_ids.length}</div></div>`;
  box.innerHTML=html;
  box.querySelectorAll('.hitem').forEach(el=>el.onclick=()=>{sel=el.dataset.p;renderSide();renderMain()});
}

// Ordering for every card list in the app:
//   1. anything already checked off sinks to the very bottom
//   2. in the "independent" bucket the cumulative ones come first, they are the
//      long grind you can start now and finish later
//   3. rarest first, so the hard ones sit at the top of a fresh list
function sortCards(ids, opts){
  opts = opts || {};
  return ids.slice().sort((x,y)=>{
    const a=ACH[x], b=ACH[y];
    const da=done.has(x)?1:0, db=done.has(y)?1:0;
    if(da!==db) return da-db;
    if(opts.cumulativeFirst){
      const ca=(a.c==='collect')?0:1, cb=(b.c==='collect')?0:1;
      if(ca!==cb) return ca-cb;
    }
    if(opts.byDiff){
      const o=['easy','normal','hard','very hard','overkill','mayhem','death wish','below zero','death sentence'];
      const ra=o.indexOf((a.df&&a.df[0])||''), rb=o.indexOf((b.df&&b.df[0])||'');
      if(ra!==rb) return (ra<0?99:ra)-(rb<0?99:rb);
    }
    return (a.p??999)-(b.p??999);
  });
}

function cardHtml(i){
  const a=ACH[i], isDone=done.has(i);
  const ru=(lang==='ru'&&a.nr)?`<span class="orig">${esc(a.n)}</span>`:
           (lang==='en'&&a.nr)?`<span class="orig">${esc(a.nr)}</span>`:'';
  const cond=(lang==='ru'&&a.dr)?a.dr:a.d;
  const conden=(lang==='ru'&&a.dr)?a.d:'';
  const badges=[];
  if(a.c==='crew')badges.push('<span class="b crew">нужны 4 игрока</span>');
  if(a.sc==='lobby')badges.push('<span class="b lob">только лобби</span>');
  if(a.ex)badges.push('<span class="b ex">ровно эта сложность</span>');
  if(a.dy)badges.push(`<span class="b day">${a.dy}-й день</span>`);
  if(a.p!=null)badges.push(`<span class="b">${a.p}%</span>`);
  const rw=a.r||{},rt=[];
  if(rw.masks)rt.push('маска: '+rw.masks.join(', '));
  if(rw.patterns)rt.push('рисунок: '+rw.patterns.join(', '));
  if(rw.materials)rt.push('материал: '+rw.materials.join(', '));
  if(rw.weapons)rt.push('оружие: '+rw.weapons.join(', '));
  if(rw.characters)rt.push('персонаж: '+rw.characters.join(', '));
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
    ${a.img?`<img src="${esc(a.img)}" alt="" loading="lazy">`:'<img alt="">'}
    <div class="body">
      <div class="nm">${esc(lang==='ru'?(a.nr||a.n):a.n)}${ru}</div>
      <div class="cond">${esc(cond)}</div>
      ${conden?`<div class="conden">${esc(conden)}</div>`:''}
      ${badges.length?`<div class="badges">${badges.join('')}</div>`:''}
      ${dep}
    </div></div>`;
}

function renderGroups(main,ids,title,sub){
  if(!ids.length){main.insertAdjacentHTML('beforeend','<div class="empty">Нет достижений</div>');return}
  const byCat={},allCats={};
  for(const i of ids){const a=ACH[i];allCats[a.c]=(allCats[a.c]||0)+1;
    if(chips.size&&!chips.has(a.c))continue;(byCat[a.c]=byCat[a.c]||[]).push(i)}
  const chipHtml=Object.entries(allCats).sort((a,b)=>b[1]-a[1]).map(([c,n])=>
    `<span class="chip ${chips.has(c)?'on':''}" data-c="${c}">${esc(D.category_labels[c]||c)} <span class="n">${n}</span></span>`).join('');
  main.insertAdjacentHTML('beforeend',`<div class="chips">${chipHtml}${
    chips.size?'<span class="chip" data-c="__clear">сбросить фильтр</span>':''}</div>`);
  main.querySelectorAll('.chip').forEach(el=>el.onclick=()=>{const c=el.dataset.c;
    if(c==='__clear')chips.clear();else chips.has(c)?chips.delete(c):chips.add(c);renderMain()});
  const order=D.category_priority;
  const keys=Object.keys(byCat).sort((a,b)=>{
    const ia=order.indexOf(a),ib=order.indexOf(b);return (ia<0?99:ia)-(ib<0?99:ib)||byCat[b].length-byCat[a].length});
  for(const c of keys){
    const list=byCat[c].sort((x,y)=>{
      const a=ACH[x],b=ACH[y];
      return ((a.p??999)-(b.p??999))||a.n.localeCompare(b.n)});
    main.insertAdjacentHTML('beforeend',
      `<div class="sect">${esc(D.category_labels[c]||c)} — ${list.length}</div>
       <div class="cards">${list.map(cardHtml).join('')}</div>`);
  }
}

function renderMain(){
  const main=document.getElementById('main');
  if(sel==='__global__'){
    const P=D.parallel||{};
    const inh=[...(P.heist||[]),...(P.anywhere||[])];
    const lob=P.lobby||[];
    main.innerHTML=`<div class="topbar">
        <div class="cellname"><div class="lbl">список</div>
          <div class="nm">Общие и накопительные</div>
          <div class="sub2">делаются в любом хайсте, кроме лобби</div></div>
        <div class="cellruns"><div class="lbl">всего</div><div class="big">${inh.length}</div></div>
      </div>
      <div id="maininner"><div class="colmain">
        <div class="sect">Делаются в хайсте — ${inh.length}</div>
        <div class="cards">${sortCards(inh,{cumulativeFirst:true}).map(cardHtml).join('')}</div>
        <div class="sect lobby">Только в лобби / убежище — ${lob.length}</div>
        <div class="cards">${sortCards(lob).map(cardHtml).join('')}</div>
      </div><div class="colside"></div></div>`;
    return;
  }
  const h=HEISTS.find(x=>x.page===sel);
  if(!h){main.innerHTML='<div class="empty">Выбери хайст слева</div>';return}

  // which variant is active
  let ids=h.ids, planSrc=h.plan, activeVar=null;
  if(h.variants&&h.variants.length){
    if(vsel[sel]===undefined||!h.variants.some(v=>v.ru===vsel[sel])) vsel[sel]=h.variants[0].ru;
    activeVar=h.variants.find(v=>v.ru===vsel[sel]);
    if(activeVar){ ids=activeVar.ids; if(activeVar.plan) planSrc=activeVar.plan; }
  }
  const runs=(planSrc.runs||[]).length;

  // (5) masks and kills connected to THIS heist
  const gearKills=h.ids.filter(i=>{
    const a=ACH[i], rw=a.r||{};
    return (rw.masks||rw.patterns||rw.materials||rw.weapons||rw.characters||[]).length || a.c==='count';
  });
  // (3) anything that can be done whenever you like
  const P=D.parallel||{};
  const independent=[...(P.heist||[]),...(P.anywhere||[])];

  let html=`<div class="topbar">
    <div class="cellname"><div class="lbl">название</div>
      <div class="nm">${esc(lang==='ru'&&h.name_ru?h.name_ru:h.name)}${(h.name_ru&&h.name_ru!==h.name)?`<span class="orig">${esc(h.name)}</span>`:''}</div>
      <div class="sub2">${esc(h.contractor)} · ${h.mode==='stealth'?'тихий':h.mode==='loud'?'шумный':'любой режим'}${h.classic?' · классический':''}
        ${h.variant_packs&&h.variant_packs.length?' · набор: '+h.variant_packs.join(', '):''}
        · <a href="${esc(h.wiki)}" target="_blank">вики ↗</a></div></div>
    <div class="cellruns"><div class="lbl">кол-во проходов</div>
      <div class="big">${runs}</div>
      <div class="sub2">${cnt(h.ids)}/${h.ids.length} отмечено</div></div>
  </div>
  <div id="maininner"><div class="colmain">`;

  if(lang==='ru'&&h.desc_ru) html+=`<p class="hdesc">${esc(h.desc_ru)}</p>`;

  // variant picker
  if(h.variants&&h.variants.length){
    const kindTitle=h.variant_kind==='loot'?'Разновидности добычи'
                   : h.variant_kind==='day'?'Дни ограбления':'Разновидности карты';
    html+=`<div class="sect">${kindTitle} — ${h.variants.length}</div>
      <div class="vtabs">${h.variants.map(v=>`<div class="vtab ${v.ru===vsel[sel]?'on':''}"
        data-v="${esc(v.ru)}">${esc(v.ru)}<span class="en">${esc(v.en)}</span>
        <span class="n">${v.ids.length} достижений</span></div>`).join('')}</div>`;
    html+= h.variant_kind==='loot'
      ? `<p class="vnote">Разновидность выбирается при взятии контракта, и у каждой свой набор —
         на золоте ячейки не закрыть.</p>`
      : h.variant_kind==='day'
      ? `<p class="vnote">Контракт многоходовый: «на 2 день» берутся, только если ты доиграл до второго дня.</p>`
      : `<p class="vnote">У каждой карты свой набор, ничего не смешано.</p>`;
  }

  // run plan
  const pl=planSrc.runs||[];
  if(pl.length){
    const grind=(planSrc.grind||[]).map(g=>`<b>${esc(g.name)}</b> ×${g.times}`).join(', ');
    html+=`<div class="plan">
      <h3>Проходов для всех достижений: ${pl.length}${activeVar?' <span style="font-weight:400;color:var(--dim)">— «'+esc(activeVar.ru)+'»</span>':''}</h3>
      <div class="sub">Сложности складываются, несовместимые условия требуют отдельного прохода.
        Максимум — ${esc(planSrc.max_diff)}.</div>
      <div class="runs">${pl.map((r,k)=>`<div class="run">
        <div class="no">Проход ${k+1}</div><div class="cfg">${esc(r.label)}</div>
        <ul>${r.ach.map(n=>`<li>${esc(n)}</li>`).join('')}</ul></div>`).join('')}</div>
      ${grind?`<div class="grind">Отдельно требует повторов: ${grind}</div>`:''}</div>`;
  }

  // (4) what THIS run/variant gets you
  html+=`<div class="sect">Достижения на этом ограблении — ${ids.length}${activeVar?' («'+esc(activeVar.ru)+'»)':''}</div>`;
  if(ids.length) html+=`<div class="cards">${sortCards(ids).map(cardHtml).join('')}</div>`;
  else html+=`<div class="empty">У этого хайста нет достижений</div>`;

  // (6) everything on this heist, across every variant
  const others=(h.variants||[]).filter(v=>!activeVar||v.ru!==activeVar.ru);
  if(others.length){
    html+=`<div class="sect">Остальные разновидности этого хайста — ${others.reduce((n,v)=>n+v.ids.length,0)}</div>`;
    for(const v of others)
      html+=`<div class="sect small">${esc(v.ru)} (${esc(v.en)}) — ${v.ids.length}</div>
              <div class="cards">${sortCards(v.ids).map(cardHtml).join('')}</div>`;
  }
  html+=`<div class="sect">Общий список достижений хайста — ${h.ids.length}</div>
         <div class="chips"><span class="chip on">все ${h.ids.length}</span></div>
         <div class="cards">${sortCards(h.ids).map(cardHtml).join('')}</div>`;
  html+='</div><div class="colside">';

  // (5) masks and kills
  html+=`<div class="sect shared">Маски и убийства на этом хайсте — ${gearKills.length}</div>
    <p class="vnote">То, что ради этого хайста и качается: награды за маски, снаряжение
     и счётчики убийств.</p>
    ${gearKills.length?`<div class="cards">${sortCards(gearKills).map(cardHtml).join('')}</div>`
                     :'<div class="empty">Нет таких достижений</div>'}`;

  // (3) independent
  html+=`<div class="sect">Независимые — можно делать когда угодно — ${independent.length}</div>
    <p class="vnote">Килы, сумки, навыки, репутация. Засчитываются в любом заходе,
     к этому хайсту не привязаны.</p>
    ${(()=>{const s=sortCards(independent,{cumulativeFirst:true});
        return `<div class="cards">${s.slice(0,60).map(cardHtml).join('')}</div>`
        +(s.length>60?`<div class="empty">…и ещё ${s.length-60}</div>`:'');})()}`;
  html+='</div></div>';

  main.innerHTML=html;
  main.querySelectorAll('.vtab').forEach(el=>el.onclick=()=>{vsel[sel]=el.dataset.v;renderMain()});
}

document.getElementById('main').addEventListener('change',e=>{
  const c=e.target.closest('.card');if(!c)return;
  const i=+c.dataset.i;e.target.checked?done.add(i):done.delete(i);
  save();renderSide();updateStats();renderMain()});
document.getElementById('q').oninput=e=>{
  query=e.target.value;document.getElementById('achresults').hidden=true;renderSide()};

// achievement search: type -> results -> click jumps to the heist it comes from
const ares=document.getElementById('achresults');
function whereOf(i){
  const a=ACH[i];
  for(const h of HEISTS){
    if(h.ids.includes(i)) return (lang==='ru'&&h.name_ru?h.name_ru:h.name);
    for(const v of (h.variants||[])) if(v.ids.includes(i))
      return (lang==='ru'&&h.name_ru?h.name_ru:h.name)+' → '+v.ru;
  }
  return (a.sc==='lobby')?'лобби / убежище':'общее, в любом хайсте';
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
    if(at>=0) hits.push({a,at});
    if(hits.length>=120) break;
  }
  hits.sort((x,y)=>x.at-y.at);
  if(!hits.length){ares.innerHTML='<div class="grp">Ничего не найдено</div>';ares.hidden=false;return}
  ares.innerHTML='<div class="grp">Найдено: '+hits.length+'</div>'+hits.map(h=>{
    const a=h.a, nm=lang==='ru'?(a.nr||a.n):a.n;
    const ix=nm.toLowerCase().indexOf(q);
    const hl=ix<0?esc(nm):esc(nm.slice(0,ix))+'<em>'+esc(nm.slice(ix,ix+q.length))+'</em>'+esc(nm.slice(ix+q.length));
    return `<button class="ares" data-i="${a.i}">
      <div class="an">${hl}</div>
      <div class="aw">${esc(whereOf(a.i))}${a.p!=null?' · '+a.p+'% игроков':''}</div>
      <div class="ac">${esc(lang==='ru'?(a.dr||a.d):a.d)}</div></button>`}).join('');
  ares.hidden=false;
  ares.querySelectorAll('.ares').forEach(b=>b.onclick=()=>{
    const i=+b.dataset.i;
    const host=HEISTS.find(h=>h.ids.includes(i)) ||
      HEISTS.find(h=>(h.variants||[]).some(v=>v.ids.includes(i)));
    ares.hidden=true;document.getElementById('heistlist').hidden=false;
    document.getElementById('qa').value='';
    if(host){ sel=host.page; renderSide(); renderMain();
      const card=[...document.querySelectorAll('.card')].find(c=>+c.dataset.i===i);
      if(card){card.scrollIntoView({block:'center'});card.style.outline='2px solid var(--acc)';
        setTimeout(()=>card.style.outline='',2200);}
    } else { sel='__global__'; renderSide(); renderMain();
      const card=[...document.querySelectorAll('.card')].find(c=>+c.dataset.i===i);
      if(card){card.scrollIntoView({block:'center'});card.style.outline='2px solid var(--acc)';
        setTimeout(()=>card.style.outline='',2200);}
    }
  });
}
document.getElementById('qa').oninput=runAchSearch;
document.getElementById('qa').addEventListener('keydown',e=>{
  if(e.key==='Escape'){e.target.value='';ares.hidden=true}});
document.getElementById('btn-lang').onclick=e=>{lang=lang==='ru'?'en':'ru';
  e.target.textContent=lang.toUpperCase();e.target.classList.toggle('on',lang==='ru');renderSide();renderMain()};
document.getElementById('btn-steam').onclick=()=>{
  done=new Set(D.done||[]); save(); renderSide(); renderMain(); updateStats(); };
document.getElementById('btn-reset').onclick=()=>{if(confirm('Сбросить все отметки?')){done=new Set();save();renderSide();renderMain();updateStats()}};
function updateStats(){document.getElementById('s-steamd').textContent=fromSteam;
  document.getElementById('s-heist').textContent=HEISTS.length;
  document.getElementById('s-ach').textContent=ACH.length;
  document.getElementById('s-done').textContent=done.size;
  document.getElementById('bar').style.width=(done.size/ACH.length*100)+'%'}
renderSide();updateStats();sel='GO Bank';renderSide();renderMain();
</script>
</body></html>
"""

out = HTML.replace("__PAYLOAD__", payload.replace("</script>", "<\\/script>"))
path = os.path.join("payday", "achievements.html")
open(path, "w", encoding="utf-8").write(out)
print("written:", path, os.path.getsize(path) // 1024, "KB")