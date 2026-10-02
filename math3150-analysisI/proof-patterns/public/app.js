/* ------------------------------------------------------------ state */
const MODS = [
  {id:"pattern", name:"Claim → technique", n:PATTERNS.length, h:"Claim → technique", p:"Read the claim. Pick the move you would open with."},
  {id:"negate", name:"Negate it", n:NEGATIONS.length, h:"Negate it", p:"Pick the correct negation. You need this for divergence, not-Cauchy and contradiction proofs."},
  {id:"order", name:"Put it in order", n:PROOFS.length, h:"Put it in order", p:"Tap the steps in the order they belong. Tap a placed step to send it back."},
  {id:"flaw", name:"Find the flaw", n:FLAWS.length, h:"Find the flaw", p:"Each proof has exactly one bad line. Tap it. These are the guide's point-losing mistakes."},
  {id:"tf", name:"True or false", n:TF.length, h:"True or false", p:"Decide, then check the justification or counterexample you'd write."},
  {id:"defs", name:"Definitions", n:DEFS.length, h:"State it exactly", p:"Write the definition from memory, then compare. Be honest when you grade yourself."},
];
// Progress lives on disk (progress.json) via the local server.
let store = {};
let active = "pattern";
let saveTimer = null;
function save(){
  store._tab = active;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fetch("/api/progress", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(store)})
      .catch(() => console.warn("Progress not saved: is the server still running?"));
  }, 250);
}
function mstate(id){ return store[id] || (store[id] = {i:0, right:{}, order:null}); }

const $ = (s, el=document) => el.querySelector(s);
const h = (tag, attrs={}, html="") => { const e=document.createElement(tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (html) e.innerHTML = html; return e; };
function shuffle(a, seed){ const r=[...a]; let s=seed*9301+49297; for(let i=r.length-1;i>0;i--){ s=(s*9301+49297)%233280; const j=Math.floor(s/233280*(i+1)); [r[i],r[j]]=[r[j],r[i]]; } return r; }
function typeset(el){ if (window.MathJax && MathJax.typesetPromise) { MathJax.typesetClear && MathJax.typesetClear([el]); MathJax.typesetPromise([el]).catch(()=>{}); } }
function score(id){ const s=mstate(id); return Object.values(s.right).filter(Boolean).length; }

/* ------------------------------------------------------------ chrome */
function renderTabs(){
  const t = $("#tabs"); t.innerHTML = "";
  MODS.forEach(m => {
    const b = h("button", {class:"tab", role:"tab", "aria-selected": String(m.id===active), id:"tab-"+m.id},
      `${m.name}<span class="sc">${score(m.id)}/${m.n}</span>`);
    b.onclick = () => { active = m.id; save(); render(); };
    t.appendChild(b);
  });
}
function shell(mod, idx){
  const st = $("#stage"); st.innerHTML = "";
  st.appendChild(h("div", {class:"intro"}, `<div><h2>${mod.h}</h2><p>${mod.p}</p></div>`));
  const card = h("div", {class:"card"});
  card.appendChild(h("div", {class:"meta"}, `<span>${String(idx+1).padStart(2,"0")} / ${String(mod.n).padStart(2,"0")}</span><span>${score(mod.id)} correct so far</span>`));
  st.appendChild(card);
  return card;
}
function navRow(mod, after){
  const s = mstate(mod.id);
  const row = h("div", {class:"row"});
  const prev = h("button", {class:"btn ghost", id:"prev-"+mod.id}, "Previous");
  prev.disabled = s.i===0;
  prev.onclick = () => { s.i--; s.order=null; save(); render(); };
  const next = h("button", {class:"btn", id:"next-"+mod.id}, s.i===mod.n-1 ? "Start over" : "Next");
  next.onclick = () => { s.i = (s.i+1) % mod.n; s.order=null; save(); render(); };
  row.append(prev, next);
  if (after) row.insertBefore(after, next);
  return row;
}
function feedback(kind, verdict, body, opener){
  const f = h("div", {class:"fb "+kind});
  f.innerHTML = `<span class="verdict">${verdict}</span><p>${body}</p>` + (opener ? `<div class="opener"><b>Write this first</b>${opener}</div>` : "");
  return f;
}
function mark(id, i, ok){ const s=mstate(id); if (s.right[i]===undefined) s.right[i]=ok; save(); renderTabs(); }

/* ------------------------------------------------------------ modules */
function renderPattern(mod){
  const s = mstate(mod.id), it = PATTERNS[s.i], card = shell(mod, s.i);
  card.appendChild(h("p", {class:"prompt"}, `<small>Prove or decide:</small>${it.c}`));
  const opts = h("div", {class:"opts"});
  Object.entries(TECH).forEach(([k,t]) => {
    const b = h("button", {class:"opt", "data-k":k}, t.name);
    b.onclick = () => {
      const ok = k===it.a;
      opts.querySelectorAll(".opt").forEach(o => { o.disabled=true; if (o.dataset.k===it.a) o.classList.add("right"); else if (o===b) o.classList.add("wrong"); else o.classList.add("dim"); });
      mark(mod.id, s.i, ok);
      const fb = feedback(ok?"good":"bad", ok?"Right move":"Better move: "+TECH[it.a].name, it.why, TECH[it.a].first);
      card.insertBefore(fb, card.lastChild); typeset(fb);
    };
    opts.appendChild(b);
  });
  card.append(opts, navRow(mod));
}
function renderChoice(mod, items, promptLabel){
  const s = mstate(mod.id), it = items[s.i], card = shell(mod, s.i);
  card.appendChild(h("p", {class:"prompt"}, `<small>${promptLabel}</small>${it.s}`));
  const opts = h("div", {class:"opts stack"});
  shuffle(it.o.map((o,i)=>({o,i})), s.i+3).forEach(({o,i}) => {
    const b = h("button", {class:"opt", "data-i":i}, o);
    b.onclick = () => {
      const ok = i===it.a;
      opts.querySelectorAll(".opt").forEach(x => { x.disabled=true; if (+x.dataset.i===it.a) x.classList.add("right"); else if (x===b) x.classList.add("wrong"); else x.classList.add("dim"); });
      mark(mod.id, s.i, ok);
      const fb = feedback(ok?"good":"bad", ok?"Correct":"Not quite", it.why);
      card.insertBefore(fb, card.lastChild); typeset(fb);
    };
    opts.appendChild(b);
  });
  card.append(opts, navRow(mod));
}
function renderOrder(mod){
  const s = mstate(mod.id), it = PROOFS[s.i], card = shell(mod, s.i);
  card.appendChild(h("p", {class:"prompt"}, `<small>Rebuild the proof of</small>${it.t}`));
  if (!s.order) { s.order = {placed:[], checked:false}; save(); }
  const pool = shuffle(it.s.map((_,i)=>i), s.i+11).filter(i => !s.order.placed.includes(i));
  const wrapP = h("div"), wrapR = h("div");
  wrapP.appendChild(h("p", {class:"slot-label"}, "Your proof"));
  wrapR.appendChild(h("p", {class:"slot-label"}, "Steps left"));
  const placed = h("ol", {class:"lines placed"}), rest = h("ul", {class:"lines"});
  if (!s.order.placed.length) wrapP.appendChild(h("div", {class:"empty"}, "Tap the step that comes first."));
  s.order.placed.forEach((i,pos) => {
    const li = h("li", {}, `<span>${it.s[i]}</span>`);
    if (s.order.checked) { li.classList.add(i===pos?"right":"wrong","locked"); }
    else li.onclick = () => { s.order.placed.splice(pos,1); save(); render(); };
    placed.appendChild(li);
  });
  pool.forEach(i => {
    const li = h("li", {}, `<span>${it.s[i]}</span>`);
    li.onclick = () => { if (s.order.checked) return; s.order.placed.push(i); save(); render(); };
    rest.appendChild(li);
  });
  if (s.order.placed.length) wrapP.appendChild(placed);
  card.appendChild(wrapP);
  if (pool.length) { wrapR.appendChild(rest); card.appendChild(wrapR); }
  const check = h("button", {class:"btn ghost", id:"check-order"}, s.order.checked ? "Try again" : "Check order");
  check.disabled = !s.order.checked && pool.length>0;
  check.onclick = () => {
    if (s.order.checked) { s.order = {placed:[], checked:false}; save(); render(); return; }
    s.order.checked = true; const ok = s.order.placed.every((v,p)=>v===p);
    mark(mod.id, s.i, ok); save(); render();
  };
  if (s.order.checked) {
    const ok = s.order.placed.every((v,p)=>v===p);
    const body = ok ? it.note : it.note + `<br><br><b>Correct order:</b><ol style="margin:6px 0 0;padding-left:1.3em">${it.s.map(x=>`<li>${x}</li>`).join("")}</ol>`;
    card.appendChild(feedback(ok?"good":"bad", ok?"Proof holds":"Some steps are out of place", body));
  }
  card.appendChild(navRow(mod, check));
  typeset(card);
}
function renderFlaw(mod){
  const s = mstate(mod.id), it = FLAWS[s.i], card = shell(mod, s.i);
  card.appendChild(h("p", {class:"prompt"}, `<small>Which line breaks the proof?</small>${it.t}`));
  const box = h("div", {class:"proofbox"});
  it.l.forEach((line, i) => {
    const b = h("button", {class:"opt", "data-i":i}, `<span class="ln">${i+1}</span><span>${line}</span>`);
    b.onclick = () => {
      const ok = i===it.a;
      box.querySelectorAll(".opt").forEach(x => { x.disabled=true; if (+x.dataset.i===it.a) x.classList.add("right"); else x.classList.add(x===b?"wrong":"dim"); });
      mark(mod.id, s.i, ok);
      const fb = feedback(ok?"good":"bad", ok?"Found it":"The bad line is "+(it.a+1), it.why);
      card.insertBefore(fb, card.lastChild); typeset(fb);
    };
    box.appendChild(b);
  });
  card.append(box, navRow(mod));
}
function renderTF(mod){
  const s = mstate(mod.id), it = TF[s.i], card = shell(mod, s.i);
  card.appendChild(h("p", {class:"prompt"}, `<small>True or false?</small>${it.s}`));
  const opts = h("div", {class:"opts"});
  [true,false].forEach(v => {
    const b = h("button", {class:"opt", "data-v":String(v)}, v ? "True: I can prove it" : "False: I have a counterexample");
    b.onclick = () => {
      const ok = v===it.a;
      opts.querySelectorAll(".opt").forEach(x => { x.disabled=true; if (x.dataset.v===String(it.a)) x.classList.add("right"); else x.classList.add(x===b?"wrong":"dim"); });
      mark(mod.id, s.i, ok);
      const fb = feedback(ok?"good":"bad", (it.a?"True":"False") + (ok?" — correct":""), it.why);
      card.insertBefore(fb, card.lastChild); typeset(fb);
    };
    opts.appendChild(b);
  });
  card.append(opts, navRow(mod));
}
function renderDefs(mod){
  const s = mstate(mod.id), it = DEFS[s.i], card = shell(mod, s.i);
  card.appendChild(h("p", {class:"prompt"}, `<small>State precisely:</small>${it.t}`));
  const ta = h("textarea", {class:"recall", id:"recall-"+s.i, placeholder:"Write it out word for word, quantifiers included…"});
  card.appendChild(ta);
  const reveal = h("button", {class:"btn ghost", id:"reveal"}, "Show the definition");
  reveal.onclick = () => {
    reveal.disabled = true;
    const ans = h("div", {class:"answer"}, it.d);
    const grade = h("div", {class:"row"});
    const yes = h("button", {class:"btn", id:"got-it"}, "I had it exactly");
    const no = h("button", {class:"btn ghost", id:"missed"}, "I missed something");
    yes.onclick = () => { mark(mod.id, s.i, true); s.right[s.i]=true; save(); renderTabs(); yes.disabled=no.disabled=true; };
    no.onclick = () => { s.right[s.i]=false; save(); renderTabs(); yes.disabled=no.disabled=true; };
    grade.append(no, yes);
    card.insertBefore(ans, card.lastChild); card.insertBefore(grade, card.lastChild); typeset(ans);
  };
  card.appendChild(navRow(mod, reveal));
}

function render(){
  renderTabs();
  const mod = MODS.find(m=>m.id===active) || MODS[0];
  ({pattern:renderPattern, order:renderOrder, flaw:renderFlaw, defs:renderDefs,
    negate:m=>renderChoice(m, NEGATIONS, "Negate:"), tf:renderTF})[mod.id](mod);
  typeset($("#stage"));
}

/* ------------------------------------------------------------ cheat sheet */
const SHEET = [
  [R`\(S=T\) (sets)`, "double"], [R`“for all \(n\ge n_0\)”`, "induction"], [R`“\(x\) is irrational”, “no such …”`, "contra"],
  [R`“Is it always true?” (you suspect not)`, "counter"], [R`\(M=\sup S\)`, "supeps"], [R`\(\sup A\le\) something`, "ubound"],
  [R`\(\lim x_n=L\)`, "epsN"], [R`\(\lim x_n=\infty\)`, "MN"], [R`Converges, limit unknown, monotone`, "mct"],
  [R`Converges, limit unknown, not monotone`, "cauchy"], [R`Diverges (sums, slow growth)`, "notcauchy"], [R`Diverges (oscillates)`, "subseq"], [R`\(|a|\le c\)`, "abs"],
];
const tb = $("#sheet tbody");
SHEET.forEach(([c,k]) => tb.appendChild(h("tr", {}, `<td>${c}</td><td>${TECH[k].name}</td><td>${TECH[k].first}</td>`)));

$("#reset").onclick = () => { store = {}; save(); render(); };

fetch("/api/progress").then(r => r.ok ? r.json() : {}).catch(() => ({})).then(saved => {
  store = saved || {};
  if (MODS.some(m => m.id === store._tab)) active = store._tab;
  render();
  if (window.MathJax && MathJax.startup) MathJax.startup.promise.then(() => typeset(document.body));
});
