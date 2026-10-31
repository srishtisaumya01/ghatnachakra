"use strict";
/* Ghatnachakra – single page app (no build step, static hosting). All dynamic text goes through textContent, so book text
   and user names can never be interpreted as HTML. The only innerHTML is for the fixed icon paths below. */

/* ---------- tiny helpers ---------- */
const $ = (s, el = document) => el.querySelector(s);
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, "");
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return e;
}
const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
const fmtTime = (s) => { s = Math.max(0, Math.round(s)); const m = Math.floor(s / 60); return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };
const chapterOf = (qid) => qid.slice(0, qid.lastIndexOf("-"));
const subjectOf = (qid) => qid.slice(0, qid.indexOf("-"));
const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const nf = (n) => Number(n).toLocaleString("en-IN");

const ICONS = {
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>',
  dash: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  plus: '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
  warn: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  chart: '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5V22h16"/>',
  layers: '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  server: '<rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.01M7 17.5h.01"/>',
  db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10"/>',
  cog: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"/>',
  close: '<path d="M18 6 6 18M6 6l12 12"/>',
  home: '<path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/>',
};
function icon(name) {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("class", "icon"); s.setAttribute("aria-hidden", "true");
  s.setAttribute("fill", "none"); s.setAttribute("stroke", "currentColor"); s.setAttribute("stroke-width", "2");
  s.setAttribute("stroke-linecap", "round"); s.setAttribute("stroke-linejoin", "round");
  s.innerHTML = ICONS[name] || ""; // fixed strings above, never user data
  return s;
}
function logo() {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 32 32"); s.setAttribute("aria-hidden", "true");
  s.innerHTML = '<circle cx="16" cy="16" r="13" fill="none" stroke="currentColor" stroke-width="2.5"/><path d="M16 3v9M16 20v9M3 16h9M20 16h9M6.8 6.8l6.4 6.4M18.8 18.8l6.4 6.4M25.2 6.8l-6.4 6.4M13.2 18.8l-6.4 6.4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="16" cy="16" r="3.4" fill="currentColor"/>';
  return h("a", { class: "logo", href: "#/", "aria-label": "Ghatnachakra home" }, s, h("span", {}, "Ghatnachakra"));
}

/* ---------- theme (light / dark, remembered) ---------- */
const systemDark = () => matchMedia("(prefers-color-scheme: dark)").matches;
const isDark = () => { const t = document.documentElement.getAttribute("data-theme"); return t ? t === "dark" : systemDark(); };
function toggleTheme() {
  const next = isDark() ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try { localStorage.setItem("gc_theme", next); } catch { /* private mode: still works for this visit */ }
  document.querySelectorAll("[data-themebtn]").forEach(paintThemeBtn);
}
function paintThemeBtn(b) {
  b.replaceChildren(icon(isDark() ? "sun" : "moon"));
  b.setAttribute("aria-label", isDark() ? "Switch to light mode" : "Switch to dark mode");
  b.title = isDark() ? "Light mode" : "Dark mode";
}
function themeBtn() { const b = h("button", { class: "iconbtn", "data-themebtn": "", onclick: toggleTheme }); paintThemeBtn(b); return b; }

/* ---------- API (same origin: /api/* is rewritten to the Django server, so the session cookie is first-party) ---------- */
const API = "/api/v1";
const cookie = (n) => document.cookie.split("; ").find((c) => c.startsWith(n + "="))?.slice(n.length + 1);
class ApiError extends Error { constructor(msg, status, code, fields) { super(msg); this.status = status; this.code = code; this.fields = fields || {}; } }
async function api(path, { method = "GET", body } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") { const t = cookie("ghatnachakra_csrf"); if (t) headers["X-CSRFToken"] = t; }
  let r;
  try { r = await fetch(API + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), credentials: "same-origin" }); }
  catch { throw new ApiError("Cannot reach the server. Check your connection and try again.", 0, "network"); }
  if (r.status === 204) return null;
  let data = null;
  try { data = await r.json(); } catch { /* not JSON */ }
  if (!r.ok) {
    const e = data?.error;
    if (r.status === 401 && ME && e?.code === "unauthenticated") sessionEnded();
    throw new ApiError(e?.message || `Request failed (${r.status})`, r.status, e?.code, e?.fields);
  }
  return data;
}
const post = (path, body) => api(path, { method: "POST", body });

/* ---------- state ---------- */
let ME = null; // signed-in user
let M = null; // manifest (after sign-in)
let PUB = null; // public counts for the landing page
const chTitle = {}; // chapterId -> "Subject › Chapter"
const qcache = {}; // chapterId -> questions
const qmap = {}; // qid -> question
const root = $("#root");
let T = null; // active test
let timerHandle = null;
const activeKey = () => `gc_active_${ME?.id}`;
const saveT = () => { try { localStorage.setItem(activeKey(), JSON.stringify(T)); } catch { /* ignore */ } };
const readActive = () => { try { return JSON.parse(localStorage.getItem(activeKey()) || "null"); } catch { return null; } };
const clearActive = () => { try { localStorage.removeItem(activeKey()); } catch { /* ignore */ } };

function toast(msg) { const t = h("div", { class: "toast", role: "status" }, msg); document.body.append(t); setTimeout(() => t.remove(), 3800); }
function sessionEnded() { ME = null; M = null; T = null; toast("Your session ended. Please log in again."); location.hash = "#/login"; }

async function ensureData() {
  if (M) return;
  M = await api("/data/manifest.json");
  for (const s of M.subjects) for (const c of s.chapters) chTitle[c.id] = `${s.name} › ${c.title}`;
}
async function loadChapter(id) {
  if (!qcache[id]) {
    qcache[id] = await api(`/data/q/${id}.json`);
    for (const q of qcache[id]) qmap[q.id] = q;
  }
  return qcache[id];
}
const loadChapters = (ids) => Promise.all([...new Set(ids)].map(loadChapter));
const cropUrl = (q, segs) => `${API}/crop/?book=${encodeURIComponent(q.book)}&segs=${encodeURIComponent(JSON.stringify(segs))}`;

/* ---------- question rendering ---------- */
// mode: "test" (answer hidden) | "review" (answer + explanation shown)
function questionView(q, o) {
  const { mode, chosen, onPick, number } = o;
  const isImg = q.view === "image" || (mode === "review" && q.rimg);
  const box = h("div", { class: "q" });
  box.append(h("div", { class: "meta" }, number != null ? h("b", {}, `Q${number}`) : null, h("span", {}, chTitle[chapterOf(q.id)] || ""), mode === "review" && q.exam ? h("span", {}, "· " + q.exam) : null));
  const showOrig = mode === "review" ? q.fseg : q.qseg;
  const imgEl = h("img", { class: "origimg", alt: "Original book page", loading: "lazy", src: cropUrl(q, showOrig) });
  if (isImg) {
    box.append(imgEl);
    if (mode === "test") box.append(h("p", { class: "muted", style: "margin:0 0 4px;font-size:13.5px" }, "This question is shown exactly as printed in the book."));
  } else {
    box.append(h("div", {}, h("div", { class: "stem" }, q.stem)));
  }
  const cls = (l) => {
    if (mode === "test") return chosen === l ? "sel" : "";
    if (l === q.answer) return "right";
    if (l === chosen) return "wrong";
    return "";
  };
  const pick = (l) => { if (mode === "test" && onPick) onPick(l); };
  if (isImg && mode === "review") {
    box.append(h("div", { class: "imgopts" }, q.options.map((op) => h("div", { class: "opt static " + cls(op.label) }, h("span", { class: "k" }, op.label)))));
  } else if (isImg) {
    box.append(h("div", { class: "imgopts" }, q.options.map((op) => h("button", { class: "opt " + cls(op.label), onclick: () => pick(op.label) }, h("span", { class: "k" }, op.label)))));
  } else {
    for (const op of q.options) {
      box.append(h(mode === "test" ? "button" : "div", { class: "opt " + (mode === "test" ? "" : "static ") + cls(op.label), onclick: () => pick(op.label), "data-k": op.label }, h("span", { class: "k" }, op.label), h("span", {}, op.text)));
    }
  }
  if (mode === "review") {
    const verdict = !chosen ? ["skip", "Not attempted"] : chosen === q.answer ? ["ok", "Correct"] : ["bad", "Wrong"];
    box.append(h("div", { class: "row", style: "margin:6px 0" }, h("span", { class: "pill " + verdict[0] }, verdict[1]), h("span", { class: "muted" }, `Your answer: ${chosen ? chosen.toUpperCase() : "—"} · Correct: ${q.answer.toUpperCase()}`)));
    if (!isImg && q.expl) box.append(h("div", { class: "expl" }, h("b", {}, "Explanation"), q.expl));
  }
  if (!isImg) {
    const t = h("button", { class: "btn sm", style: "margin-top:8px" }, "View original from book");
    let on = false;
    t.onclick = () => { on = !on; t.textContent = on ? "Hide original" : "View original from book"; if (on) box.insertBefore(imgEl, t.nextSibling); else imgEl.remove(); };
    box.append(t);
  }
  return box;
}

/* ============================== routing ============================== */
const PUBLIC = { "": "top", how: "how", features: "features", evaluator: "evaluator", subjects: "subjects" };
const TITLES = { dashboard: "Dashboard", new: "New test", test: "Test", history: "History", mistakes: "Mistakes", result: "Result" };
let renderSeq = 0;

async function route() {
  clearInterval(timerHandle);
  document.body.classList.remove("drawer-open");
  document.onkeydown = null;
  const seq = ++renderSeq;
  const [seg, arg] = location.hash.replace(/^#\/?/, "").split("/");
  if (seg in PUBLIC) return landing(PUBLIC[seg]);
  if (seg === "login" || seg === "signup") { if (ME) { location.hash = "#/dashboard"; return; } return authPage(seg); }
  const PRIVATE = { dashboard, new: newTest, test: runTest, history, mistakes, result };
  if (!(seg in PRIVATE)) { location.hash = ME ? "#/dashboard" : "#/"; return; }
  if (!ME) { sessionStorage.setItem("gc_next", location.hash); location.hash = "#/login"; return; }
  const view = dashShell(seg);
  try {
    await ensureData();
    if (seq !== renderSeq) return;
    await PRIVATE[seg](arg, view.main);
  } catch (e) {
    if (seq !== renderSeq) return;
    console.error(e);
    view.main.replaceChildren(h("div", { class: "notice" }, "Something went wrong: " + e.message));
  }
  if (seq === renderSeq) window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);

async function signOut() {
  try { await post("/auth/logout/"); } catch { /* ignore: the page is signed out either way */ }
  clearInterval(timerHandle);
  ME = null; M = null; T = null;
  for (const k of Object.keys(qcache)) delete qcache[k];
  for (const k of Object.keys(qmap)) delete qmap[k];
  if (location.hash === "#/") route(); else location.hash = "#/";
}

/* ============================== public site ============================== */
function pubShell(active) {
  const closeDrawer = () => document.body.classList.remove("drawer-open");
  const links = [["how", "How it works"], ["features", "Features"], ["evaluator", "Evaluator"], ["subjects", "Subjects"]];
  const linkEls = (cls) => links.map(([k, l]) => h("a", { href: `#/${k}`, class: cls + (active === k ? " on" : ""), onclick: closeDrawer }, l));
  const btns = (cls) => ME
    ? [h("a", { class: "btn primary " + cls, href: "#/dashboard", onclick: closeDrawer }, icon("dash"), "Dashboard")]
    : [h("a", { class: "btn outline " + cls, href: "#/login", onclick: closeDrawer }, icon("user"), "Log in"), h("a", { class: "btn primary " + cls, href: "#/signup", onclick: closeDrawer }, "Start practising")];
  const burger = h("button", { class: "iconbtn navburger", "aria-label": "Open menu", onclick: () => document.body.classList.add("drawer-open") }, icon("menu"));
  const drawer = h("aside", { class: "drawer", "aria-label": "Menu" },
    h("div", { class: "row", style: "justify-content:space-between" }, logo(), h("button", { class: "iconbtn", "aria-label": "Close menu", onclick: closeDrawer }, icon("close"))),
    h("nav", { class: "drawer-links", "aria-label": "Mobile" }, linkEls("")),
    h("div", { class: "row" }, h("span", { class: "muted" }, "Theme"), themeBtn()),
    h("div", { class: "dbtns" }, btns("lg")));
  const main = h("main", { class: "pub-main" }, h("div", { class: "aurora", "aria-hidden": "true" }, h("i"), h("i"), h("i")));
  root.replaceChildren(
    h("header", { class: "navwrap" }, h("div", { class: "navcard" }, logo(), h("nav", { class: "navlinks", "aria-label": "Primary" }, linkEls("")),
      h("div", { class: "navright" }, h("span", { class: "wide" }, btns("nav"), h("span", { class: "navsep", "aria-hidden": "true" })), themeBtn(), burger))),
    drawer, h("div", { class: "scrim-d", onclick: closeDrawer }), main);
  return main;
}

function node(iconName, title, desc, { hi, chips } = {}) {
  return h("div", { class: "node" + (hi ? " hi" : "") }, h("div", { class: "t" }, icon(iconName), title), desc ? h("div", { class: "d" }, desc) : null,
    chips ? h("div", { class: "chips" }, chips.map((c) => h("span", { class: "chip" }, c))) : null);
}
const arrow = (label) => h("div", { class: "arrow", "aria-hidden": "true" }, h("div", {}, h("i", {}, "→"), label));


/* ---------- landing: motion helpers ---------- */
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
function revealAll(wrap) {
  const els = [...wrap.querySelectorAll(".reveal")];
  if (reduceMotion() || !("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("in")); return; }
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
  els.forEach((e) => io.observe(e));
}
function countUp(el, to) {
  if (reduceMotion()) { el.textContent = nf(to); return; }
  const t0 = performance.now(), dur = 1300;
  const step = (t) => { const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3); el.textContent = nf(Math.round(to * e)); if (k < 1 && document.body.contains(el)) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

/* ---------- landing: "How it works" mock screens (built from the real app's look, not screenshots) ---------- */
const mockWin = (url, ...body) => h("div", { class: "win", "aria-hidden": "true" }, h("div", { class: "win-bar" }, h("i"), h("i"), h("i"), h("span", {}, url)), h("div", { class: "mock" }, body.flat(Infinity)), h("span", { class: "tagi" }, "Illustration"));
function mockChoose() {
  const subs = PUB?.subjects || [];
  const hist = subs.find((x) => x.id === "history");
  const others = subs.filter((x) => x.id !== "history").slice(0, 2);
  const chapters = ["Stone Age", "Indus Valley Civilization", "Vedic Age", "Buddhism"];
  return mockWin("ghatnachakra / new test",
    h("h5", {}, "Create a test"),
    h("div", { class: "msub" }, h("div", { class: "mh" }, h("span", { class: "cb on" }), "Indian History", h("span", { class: "c" }, hist ? `${hist.chapters} chapters` : "")),
      chapters.map((n, i) => h("div", { class: "mch" }, h("span", { class: "cb tick", style: `--t:${i * 0.45}s` }), n))),
    others.map((x) => h("div", { class: "msub" }, h("div", { class: "mh" }, h("span", { class: "cb" }), x.name, h("span", { class: "c" }, `${x.chapters} chapters`)))),
    h("div", { class: "mset" }, h("span", { class: "mchip" }, "20 questions"), h("span", { class: "mchip" }, "20 min"), h("span", { class: "mchip" }, "−0.33"), h("span", { class: "mbtn" }, "Start test")));
}
function mockTake() {
  const opts = [["a", "Kalibangan"], ["b", "Dholavira"], ["c", "Mohenjo-daro"], ["d", "Lothal"]];
  const cells = Array.from({ length: 20 }, (_, i) => {
    const n = i + 1, cls = n <= 5 ? "a" : n === 4 ? "f" : n === 7 ? "c" : "";
    return h("span", { class: (n === 4 ? "f" : cls) + (n === 8 ? " live" : ""), style: n === 8 ? "--t:0s" : null }, n);
  });
  return mockWin("ghatnachakra / test",
    h("div", { class: "mtop" }, "Indian History · 20Q", h("span", { class: "mtimer" }, "14:32"), h("span", { class: "mbtn", style: "margin-left:0;animation:none;padding:4px 10px" }, "Submit")),
    h("div", { class: "mtest" },
      h("div", {}, h("div", { class: "mq" }, h("div", { class: "mm" }, "Q7 · Indian History › Indus Valley Civilization"), h("div", { class: "mstem" }, "The Great Bath was found at which Harappan site?"),
        opts.map(([k, t]) => h("div", { class: "mopt" + (k === "c" ? " pick" : "") }, h("b", {}, k), t))),
        h("div", { class: "mnav" }, h("span", {}, "← Previous"), h("span", {}, "Mark for review"), h("span", { class: "pr" }, "Next →"))),
      h("div", { class: "mpal" }, cells)));
}
function mockResult() {
  return mockWin("ghatnachakra / result",
    h("div", { class: "mscore" }, h("div", {}, h("b", {}, "10.35"), h("small", {}, "of 20 marks")), h("div", {}, h("b", {}, "60%"), h("small", {}, "accuracy")), h("div", {}, h("b", {}, "12 · 5 · 3"), h("small", {}, "right · wrong · skipped"))),
    h("div", { class: "mbars" }, [["Ancient", 80], ["Medieval", 62], ["Modern", 48]].map(([n, v]) => h("div", {}, h("span", {}, n), h("div", { class: "mbar" }, h("i", { style: `width:${v}%` })), h("b", {}, v + "%")))),
    h("div", { class: "mrev" }, h("div", { class: "mrow" }, h("span", { class: "pill bad" }, "Wrong"), h("span", { class: "muted" }, "Your answer: B · Correct: C")), h("div", {}, "Which Harappan site had the Great Bath?"), h("div", { class: "mexp" }, "Explanation: the Great Bath was found at Mohenjo-daro.")));
}
function mockProgress() {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 200 60"); svg.setAttribute("preserveAspectRatio", "none");
  svg.innerHTML = '<defs><linearGradient id="mg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--brand)" stop-opacity=".28"/><stop offset="1" stop-color="var(--brand)" stop-opacity="0"/></linearGradient></defs><path d="M0 48 25 40 50 44 75 30 100 34 125 22 150 26 175 12 200 16V60H0Z" fill="url(#mg)"/><polyline class="mline" points="0,48 25,40 50,44 75,30 100,34 125,22 150,26 175,12 200,16" fill="none" stroke="var(--brand)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>';
  return mockWin("ghatnachakra / dashboard",
    h("div", { class: "mdash" },
      h("div", { class: "mside" }, h("span", { class: "on" }, "Dashboard"), h("span", {}, "New test"), h("span", {}, "Mistakes"), h("span", {}, "History")),
      h("div", {}, h("div", { class: "mtiles" }, h("div", {}, h("b", {}, "12"), h("small", {}, "tests")), h("div", {}, h("b", {}, "71%"), h("small", {}, "accuracy")), h("div", {}, h("b", {}, "38"), h("small", {}, "mistakes"))),
        h("div", { class: "mchart" }, svg),
        h("div", { class: "mweak" }, [["Revolt of 1857", "42%", "bad"], ["Mauryan Empire", "64%", "ok"]].map(([n, v, c]) => h("div", {}, n, h("span", { class: "pill " + c }, v)))))));
}
function howStep(n, title, desc, points, mock) {
  return h("div", { class: "how" }, h("div", { class: "how-text" }, h("div", { class: "how-num" }, n), h("h3", {}, title), h("p", {}, desc),
    h("ul", {}, points.map((t) => h("li", {}, icon("check"), t)))), mock);
}


/* ---------- landing: real screenshots of the app (light/dark variants follow the theme) ---------- */
const SNAPS = {
  desktop: [["dashboard", "Dashboard", "Score trend, subject coverage and your weakest chapters at a glance."], ["new", "Create a test", "Pick chapters from any subject, then set questions, time and marking."], ["test", "Take the test", "One question at a time with a palette, a timer and review marks."], ["result", "Result and review", "Marks, a chapter-wise result and every question with its explanation."], ["mistakes", "Mistakes notebook", "Everything you got wrong, grouped by chapter and ready to practise."]],
  mobile: [["dashboard", "Dashboard", "Tabs along the bottom keep every screen one tap away."], ["new", "Create a test", "The same chapter picker, built for thumbs."], ["test", "Take the test", "Large tap targets, a timer and the question palette."], ["result", "Your result", "Marks, accuracy and review wherever you are."]],
};
function snapImgs(form, name, alt, w, hgt) {
  return ["l", "d"].map((t) => h("img", { class: "shot-" + t, src: `shots/${form}-${name}-${t}.webp`, alt, width: w, height: hgt, loading: "lazy", decoding: "async" }));
}
function openLightbox(img) {
  const o = h("div", { class: "lb", role: "dialog", "aria-modal": "true", "aria-label": img.alt || "Screenshot" }, h("img", { src: img.currentSrc || img.src, alt: img.alt }), h("button", { class: "iconbtn lbx", "aria-label": "Close" }, icon("close")));
  const close = () => { o.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  o.onclick = close; document.addEventListener("keydown", onKey); document.body.append(o);
}
function showcase() {
  const desk = SNAPS.desktop.map(([k, t, d], i) => h("figure", { class: "snap" + (i === 0 ? " wide" : "") },
    h("div", { class: "win" }, h("div", { class: "win-bar" }, h("i"), h("i"), h("i"), h("span", {}, "ghatnachakra / " + t.toLowerCase())), snapImgs("d", k, `${t} screen of the Ghatnachakra dashboard`, 1650, 1080)),
    h("figcaption", {}, h("b", {}, t), h("span", {}, d))));
  const phones = SNAPS.mobile.map(([k, t, d]) => h("figure", { class: "snap" }, h("div", { class: "phone" }, snapImgs("m", k, `${t} screen on a phone`, 780, 1688)), h("figcaption", {}, h("b", {}, t), h("span", {}, d))));
  const box = h("div", { class: "showcase" },
    h("h3", {}, "Inside your dashboard"), h("p", { class: "muted", style: "margin:0" }, "Real screens from the app. Tap a picture to enlarge it."), h("div", { class: "snaps" }, desk),
    h("h3", { style: "margin-top:48px" }, "On your phone"), h("p", { class: "muted", style: "margin:0" }, "The whole app works on a small screen, with a tab bar for quick moves."), h("div", { class: "phones" }, phones));
  box.addEventListener("click", (e) => { if (e.target.tagName === "IMG") openLightbox(e.target); });
  return box;
}

async function landing(section) {
  const main = pubShell(section);
  const wrap = h("div", { class: "wrap" });
  main.append(wrap);
  wrap.append(h("section", { class: "hero", id: "top" },
    (() => { const w = document.createElementNS("http://www.w3.org/2000/svg", "svg"); w.setAttribute("viewBox", "0 0 32 32"); w.setAttribute("class", "hero-wheel"); w.setAttribute("aria-hidden", "true"); w.innerHTML = '<circle cx="16" cy="16" r="13" fill="none" stroke="currentColor" stroke-width="1"/><path d="M16 3v9M16 20v9M3 16h9M20 16h9M6.8 6.8l6.4 6.4M18.8 18.8l6.4 6.4M25.2 6.8l-6.4 6.4M13.2 18.8l-6.4 6.4" stroke="currentColor" stroke-width=".8"/><circle cx="16" cy="16" r="3.4" fill="currentColor"/>'; return w; })(),
    h("div", {}, h("span", { class: "eyebrow" }, "PYQ practice for competitive exams"),
      h("h1", {}, "Practise previous-year questions, ", h("em", {}, "chapter by chapter.")),
      h("p", { class: "sub" }, "Build a timed test from any chapters, submit it, and get your marks, your mistakes and your progress, test after test."),
      h("div", { class: "cta" }, ME ? h("a", { class: "btn primary lg", href: "#/new" }, "Create a test") : h("a", { class: "btn primary lg", href: "#/signup" }, "Start practising"), h("a", { class: "btn lg", href: "#/how" }, "How it works"))),
    h("div", { class: "card sample" }, h("span", { class: "tag" }, "Sample result"),
      h("div", { class: "muted", style: "font-weight:600" }, "Indian History · 20Q"),
      h("div", { class: "score", style: "margin-top:6px" }, "10.35", h("span", { class: "muted", style: "font-size:20px;font-weight:600" }, " / 20")),
      h("div", { class: "row2" }, h("div", { class: "mini" }, h("b", {}, "12"), h("span", {}, "Correct")), h("div", { class: "mini" }, h("b", {}, "5"), h("span", {}, "Wrong")), h("div", { class: "mini" }, h("b", {}, "3"), h("span", {}, "Skipped"))),
      h("div", { class: "bars" }, [["Ancient", 80], ["Medieval", 65], ["Modern", 50]].map(([n, v]) => h("div", {}, h("span", {}, n), h("div", { class: "bar acc" }, h("i", { style: `width:${v}%` })), h("span", { class: "muted" }, v + "%")))))));

  if (!PUB) { try { PUB = await api("/stats/"); } catch { PUB = null; } }
  if (!document.body.contains(wrap)) return; // the visitor navigated away while the counts loaded
  const strip = h("div", { class: "strip" });
  const figures = PUB ? [[nf(PUB.questions), "Questions"], [nf(PUB.chapters), "Chapters"], [PUB.subjects.length, "Subjects"], ["0", "Answer-key mismatches"]] : [];
  figures.forEach(([v, l]) => { const num = h("div", { class: "v" }, v); strip.append(h("div", { class: "card" }, num, h("div", { class: "l" }, l))); const n = Number(String(v).replace(/,/g, "")); if (Number.isFinite(n) && n > 0) countUp(num, n); });
  wrap.append(strip);

  wrap.append(h("section", { class: "sec", id: "how" }, h("span", { class: "eyebrow" }, "Workflow"), h("h2", {}, "How it works"),
    h("p", { class: "lead" }, "Four steps from picking chapters to learning from your mistakes. This is what each screen looks like."),
    howStep(1, "Choose chapters", "Select chapters from one or several subjects, then set how many questions you want, the time and the marking scheme.", ["Any mix of subjects in one test", "Questions, minutes and negative marking are yours to set", "Or practise only the questions you got wrong before"], mockChoose()),
    howStep(2, "Take the test", "One question at a time, with a palette that shows what you have answered and what you marked for review.", ["Mark for review, clear an answer, jump to any question", "Keyboard keys: A–D to choose, ← → to move", "Countdown timer; an unfinished test survives a refresh"], mockTake()),
    howStep(3, "Submit and get marks", "The server marks your paper against the answer key and shows what was right, wrong and skipped.", ["Score, accuracy and a chapter-wise result", "Every question reviewed with the explanation and the exam it came from", "Marks cannot be changed from the browser"], mockResult()),
    howStep(4, "Learn and repeat", "Retry what you missed, revise the mistakes notebook, and watch the trend improve test after test.", ["Retry wrong and skipped questions in one click", "Mistakes stay in the notebook until you get them right", "Score trend, subject coverage and weakest chapters"], mockProgress())));

  const feats = [
    ["layers", "Chapter-wise tests", "Pick chapters from one or several subjects, then set the number of questions and the time."],
    ["clock", "Timer and negative marking", "Practise like the real exam: a countdown and a configurable penalty (−0.33, −0.25 or none)."],
    ["check", "Instant evaluation", "Your marks, accuracy and chapter-wise result appear the moment you submit."],
    ["warn", "Mistakes notebook", "Every question you got wrong is collected. Practise them until they leave the list."],
    ["chart", "Test-wise progress", "A score trend, subject coverage and your weakest chapters, updated after every test."],
    ["image", "Original book view", "Any question can be compared with the printed page. Tables, maps and formulas are shown exactly as printed."],
  ];
  wrap.append(h("section", { class: "sec", id: "features" }, h("span", { class: "eyebrow" }, "What you get"), h("h2", {}, "Everything for focused practice"),
    h("div", { class: "cards" }, feats.map(([i, t, d]) => h("div", { class: "card feat" }, h("div", { class: "ic" }, icon(i)), h("h3", {}, t), h("p", {}, d)))), showcase()));

  wrap.append(h("section", { class: "sec", id: "evaluator" }, h("span", { class: "eyebrow" }, "Test evaluator"), h("h2", {}, "How your test is evaluated"),
    h("p", { class: "lead" }, "Marks are never calculated in your browser. The server holds the answer key and does the marking, so a result cannot be edited from the page."),
    h("div", { class: "diagram" }, h("h4", {}, "From Submit to result"),
      h("div", { class: "flow live" },
        node("target", "1 · You submit", "Only your chosen options are sent: question id, option, time spent, review flag.", { hi: true }),
        arrow("POST /attempts"),
        node("shield", "2 · Server checks", "Each answer is compared with the server-side answer key. Unknown or repeated ids are ignored."),
        arrow("mark"),
        node("check", "3 · Marks", "Right +1 · Wrong −0.33 (or your setting) · Skipped 0.", { chips: ["+1", "−0.33", "0"] }),
        arrow("save"),
        node("db", "4 · Saved to you", "The attempt and every answer are stored against your account only.")),
      h("div", { class: "flow live" },
        node("chart", "5 · Result and progress", "Score, accuracy, chapter-wise table and a review of every question with the explanation. Wrong answers go to the Mistakes notebook; your trend and weakest chapters update.", { hi: true }))),
    h("div", { class: "formula" },
      h("div", { class: "card" }, h("b", {}, "Score"), h("code", {}, "score = (correct × 1) − (wrong × penalty)"), h("p", { class: "muted", style: "margin:0;font-size:14.5px" }, "Skipped questions never cost marks.")),
      h("div", { class: "card" }, h("b", {}, "Example"), h("code", {}, "20 questions: 12 right, 5 wrong, 3 skipped\n12 − (5 × 0.33) = 10.35"), h("p", { class: "muted", style: "margin:0;font-size:14.5px" }, "Accuracy is shown as right ÷ total.")))));

  wrap.append(h("section", { class: "sec" }, h("span", { class: "eyebrow" }, "Accuracy"), h("h2", {}, "Built so that nothing is wrong"),
    h("div", { class: "trust" },
      h("div", { class: "card feat" }, h("div", { class: "ic" }, icon("shield")), h("h3", {}, "Answer keys cross-checked"), h("p", {}, "Every answer letter was compared with the answer printed on the original page. Any disagreement removed the question.")),
      h("div", { class: "card feat" }, h("div", { class: "ic" }, icon("warn")), h("h3", {}, "Doubtful questions left out"), h("p", {}, "Questions the book itself marks as having no correct option, or two answers, are not used.")),
      h("div", { class: "card feat" }, h("div", { class: "ic" }, icon("image")), h("h3", {}, "Printed page on demand"), h("p", {}, "Tables, maps and formulas appear as the printed image, and every question has a “View original” button.")))));

  const subj = h("div", { class: "cards" });
  (PUB?.subjects || []).forEach((s) => subj.append(h("div", { class: "card subj-card" }, h("b", {}, s.name), h("span", { class: "muted" }, `${s.chapters} chapters · ${nf(s.questions)} questions`))));
  wrap.append(h("section", { class: "sec", id: "subjects" }, h("span", { class: "eyebrow" }, "Question bank"), h("h2", {}, "Subjects"), h("p", { class: "lead" }, "Chapter lists follow each book's own index."), subj));

  wrap.append(h("div", { class: "band" }, h("h2", {}, "Ready for your first test?"), h("p", {}, "Create a free account and start with any chapter."), ME ? h("a", { class: "btn lg", href: "#/new" }, "Create a test") : h("a", { class: "btn lg", href: "#/signup" }, "Create an account")));
  wrap.append(h("footer", { class: "foot" }, h("div", { class: "in" }, h("span", {}, "© Ghatnachakra. A practice tool; questions are from Ghatna Chakra previous-year question books."), ME ? null : h("a", { href: "#/login" }, "Log in"))));

  wrap.querySelectorAll(".flow.live .node").forEach((n, i) => n.style.setProperty("--i", i));
  wrap.querySelectorAll(".sec > .eyebrow, .sec > h2, .sec > .lead, .diagram, .formula > .card, .band, .foot").forEach((el) => el.classList.add("reveal"));
  wrap.querySelectorAll(".cards, .trust, .strip, .snaps, .phones").forEach((grid) => [...grid.children].forEach((c, i) => { c.classList.add("reveal"); c.style.setProperty("--d", `${i * 0.08}s`); }));
  wrap.querySelectorAll(".how").forEach((row, r) => [...row.children].forEach((c, i) => { c.classList.add("reveal", (i === 0) === (r % 2 === 0) ? "from-l" : "from-r"); }));
  revealAll(wrap);
  const id = section && section !== "top" ? section : null;
  requestAnimationFrame(() => (id ? document.getElementById(id)?.scrollIntoView() : window.scrollTo(0, 0)));
}

/* ============================== login / sign up ============================== */
function authPage(mode) {
  const main = pubShell(null);
  const signup = mode === "signup";
  const f = {
    username: h("input", { id: "f-username", name: "username", autocomplete: "username", required: true, autocapitalize: "none", spellcheck: "false", placeholder: signup ? "e.g. keshav_01" : "" }),
    password: h("input", { id: "f-password", name: "password", type: "password", required: true, autocomplete: signup ? "new-password" : "current-password" }),
  };
  if (signup) f.email = h("input", { id: "f-email", name: "email", type: "email", required: true, autocomplete: "email" });
  const errs = {};
  const field = (key, label, hint) => { errs[key] = h("div", { class: "err", role: "alert" }); return h("div", { class: "field" }, h("label", { for: f[key].id }, label), f[key], hint ? h("span", { class: "hint" }, hint) : null, errs[key]); };
  const note = h("div", { class: "notice", style: "display:none", role: "alert" });
  const btn = h("button", { class: "btn primary block", type: "submit" }, signup ? "Create account" : "Log in");
  const form = h("form", { novalidate: true },
    signup ? field("email", "Email") : null,
    field("username", signup ? "Username" : "Username or email", signup ? "3–30 letters, numbers, dots or underscores." : null),
    field("password", "Password", signup ? "At least 8 characters." : null), note, btn);
  form.onsubmit = async (ev) => {
    ev.preventDefault();
    Object.values(errs).forEach((e) => (e.textContent = "")); note.style.display = "none";
    btn.disabled = true; btn.textContent = signup ? "Creating…" : "Logging in…";
    try {
      const body = { username: f.username.value.trim(), password: f.password.value, transport: "cookie" };
      if (signup) body.email = f.email.value.trim();
      const res = await post(signup ? "/auth/register/" : "/auth/login/", body);
      ME = res.user;
      const next = sessionStorage.getItem("gc_next"); sessionStorage.removeItem("gc_next");
      location.hash = next && next !== "#/login" ? next : "#/dashboard";
    } catch (e) {
      let shown = false;
      for (const [k, v] of Object.entries(e.fields || {})) if (errs[k]) { errs[k].textContent = v; shown = true; }
      if (!shown) { note.textContent = e.message; note.style.display = ""; }
      btn.disabled = false; btn.textContent = signup ? "Create account" : "Log in";
    }
  };
  main.append(h("div", { class: "auth" }, h("div", { class: "card" },
    h("h1", {}, signup ? "Create your account" : "Welcome back"),
    h("p", { class: "muted", style: "margin:0 0 18px" }, signup ? "Save your tests and track your progress." : "Log in to continue your practice."),
    form,
    h("p", { class: "alt" }, signup ? "Already have an account? " : "New here? ", h("a", { href: signup ? "#/login" : "#/signup" }, signup ? "Log in" : "Create an account")))));
  f.username.focus({ preventScroll: true });
}

/* ============================== dashboard shell ============================== */
function dashShell(seg) {
  const focus = seg === "test";
  const nav = [["dashboard", "Dashboard", "dash"], ["new", "New test", "plus"], ["mistakes", "Mistakes", "warn"], ["history", "History", "clock"]];
  const app = h("div", { class: "app" + (focus ? " focus" : "") });
  const close = () => app.classList.remove("open");
  const side = h("aside", { class: "side", "aria-label": "Main" },
    logo(),
    h("div", { class: "grp" }, "Practice"),
    nav.map(([k, l, i]) => h("a", { class: "item" + (seg === k || (seg === "result" && k === "history") ? " on" : ""), href: `#/${k}`, onclick: close }, icon(i), l)),
    h("span", { class: "sp" }),
    h("a", { class: "item", href: "#/", onclick: close }, icon("home"), "Home page"),
    h("div", { class: "me" }, h("span", { class: "avatar" }, ME.username[0]), h("div", { class: "who" }, h("b", {}, ME.username), h("span", {}, "Signed in")), h("span", { class: "sp" }),
      h("button", { class: "iconbtn", title: "Log out", "aria-label": "Log out", onclick: signOut }, icon("logout"))));
  const main = h("main", { class: "dmain" }, h("p", { class: "muted" }, "Loading…"));
  const top = h("header", { class: "dtop" },
    h("button", { class: "iconbtn menu", "aria-label": "Open menu", onclick: () => app.classList.toggle("open") }, icon("menu")),
    h("h2", {}, TITLES[seg] || ""), h("span", { class: "sp" }),
    focus ? h("a", { class: "btn sm", href: "#/dashboard", onclick: (e) => { if (!confirm("Leave the test? Your answers are saved and you can resume it from the dashboard.")) e.preventDefault(); } }, "Exit") : null,
    themeBtn());
  const bnav = h("nav", { class: "bnav", "aria-label": "Primary" }, nav.map(([k, l, i]) => h("a", { class: seg === k || (seg === "result" && k === "history") ? "on" : "", href: `#/${k}`, "aria-current": seg === k ? "page" : null }, icon(i), l)));
  app.append(side, h("div", { class: "mainCol" }, top, main), bnav, h("div", { class: "scrim", onclick: close }));
  root.replaceChildren(app);
  return { main };
}

/* ---------- dashboard / progress ---------- */
function lineChart(points) {
  const W = 700, Hh = 170, P = 28;
  if (!points.length) return h("p", { class: "muted" }, "Take your first test to see your trend here.");
  const x = (i) => P + (points.length === 1 ? (W - 2 * P) / 2 : (i * (W - 2 * P)) / (points.length - 1));
  const y = (v) => Hh - P - ((Hh - 2 * P) * v) / 100;
  const ns = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", `0 0 ${W} ${Hh}`); s.setAttribute("class", "chart"); s.setAttribute("role", "img"); s.setAttribute("aria-label", "Accuracy of your recent tests");
  const add = (tag, attrs, text) => { const e = document.createElementNS(ns, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text) e.textContent = text; s.append(e); return e; };
  for (const v of [0, 25, 50, 75, 100]) { add("line", { x1: P, x2: W - P, y1: y(v), y2: y(v), stroke: "currentColor", "stroke-opacity": ".12" }); add("text", { x: 2, y: y(v) + 4, "font-size": 11, fill: "currentColor", "fill-opacity": ".6" }, v + "%"); }
  add("polyline", { points: points.map((p, i) => `${x(i)},${y(p.v)}`).join(" "), fill: "none", stroke: "var(--brand)", "stroke-width": 2.5 });
  points.forEach((p, i) => { const c = add("circle", { cx: x(i), cy: y(p.v), r: 4, fill: "var(--brand)" }); const t = document.createElementNS(ns, "title"); t.textContent = `${p.label}: ${p.v}%`; c.append(t); });
  return s;
}

async function dashboard(_arg, app) {
  const [attempts, qstats] = await Promise.all([api("/attempts/"), api("/qstats/")]);
  const done = attempts.slice().reverse();
  const tq = done.reduce((a, x) => a + x.total, 0), tc = done.reduce((a, x) => a + x.correct, 0);
  const chS = {};
  for (const [qid, s] of Object.entries(qstats)) { const c = (chS[chapterOf(qid)] ||= { seen: 0, c: 0, w: 0 }); c.seen++; c.c += s.c; c.w += s.w; }
  const wrongNow = Object.values(qstats).filter((s) => s.last === "wrong").length;
  const seenTotal = Object.keys(qstats).length;
  const allTotal = M.subjects.reduce((a, s) => a + s.chapters.reduce((b, c) => b + c.count, 0), 0);

  const stat = (v, l) => h("div", { class: "card stat" }, h("div", { class: "v" }, v), h("div", { class: "l" }, l));
  const view = h("div", {}, h("div", { class: "hello" }, h("h1", {}, `Welcome back, ${ME.username}`), h("span", { class: "sp" }), h("a", { class: "btn primary", href: "#/new" }, icon("plus"), "New test")));
  const active = readActive();
  if (active?.qids?.length) view.append(h("div", { class: "notice" }, `You have an unfinished test (${active.name}). `, h("a", { href: "#/test" }, "Resume it →")));
  view.append(h("div", { class: "grid g4" }, stat(done.length, "Tests taken"), stat(done.length ? pct(tc, tq) + "%" : "—", "Overall accuracy"), stat(`${nf(seenTotal)} / ${nf(allTotal)}`, "Questions practised"), stat(wrongNow, "Mistakes to revisit")));
  view.append(h("h2", {}, "Test-wise score trend"), h("div", { class: "card" }, lineChart(done.slice(-30).map((a) => ({ v: pct(a.correct, a.total), label: a.name })))));

  const subjRows = M.subjects.map((s) => {
    let seen = 0, c = 0, w = 0, tot = 0;
    for (const ch of s.chapters) { const x = chS[ch.id]; tot += ch.count; if (x) { seen += x.seen; c += x.c; w += x.w; } }
    return h("tr", {}, h("td", {}, s.name), h("td", { class: "num" }, `${seen}/${tot}`), h("td", {}, h("div", { class: "bar" }, h("i", { style: `width:${pct(seen, tot)}%` }))), h("td", { class: "num" }, c + w ? pct(c, c + w) + "%" : "—"), h("td", {}, h("div", { class: "bar acc" }, h("i", { style: `width:${pct(c, c + w)}%` }))));
  });
  view.append(h("h2", {}, "Subject-wise"), h("div", { class: "card", style: "overflow-x:auto" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Subject"), h("th", { class: "num" }, "Covered"), h("th", {}, ""), h("th", { class: "num" }, "Accuracy"), h("th", {}, ""))), h("tbody", {}, subjRows))));

  const weak = [];
  for (const s of M.subjects) for (const ch of s.chapters) { const x = chS[ch.id]; if (x && x.c + x.w >= 5) weak.push({ s, ch, acc: pct(x.c, x.c + x.w), n: x.c + x.w }); }
  weak.sort((a, b) => a.acc - b.acc);
  view.append(h("h2", {}, "Weakest chapters"), h("div", { class: "card" }, weak.length ? h("table", {}, h("tbody", {}, weak.slice(0, 8).map((w) => h("tr", {}, h("td", {}, w.s.name + " › " + w.ch.title), h("td", { class: "num" }, w.n + " answered"), h("td", { class: "num" }, h("span", { class: "pill " + (w.acc >= 60 ? "ok" : "bad") }, w.acc + "%")))))) : h("p", { class: "muted", style: "margin:0" }, "Answer at least 5 questions in a chapter to see it ranked here.")));
  view.append(h("h2", {}, "Recent tests"), recentTable(attempts.slice(0, 6)));
  app.replaceChildren(view);
}

function recentTable(list) {
  if (!list.length) return h("div", { class: "card" }, h("p", { class: "muted", style: "margin:0 0 6px" }, "No tests yet."), h("a", { href: "#/new" }, "Create your first test →"));
  return h("div", { class: "card", style: "overflow-x:auto" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Test"), h("th", {}, "Date"), h("th", { class: "num" }, "Score"), h("th", { class: "num" }, "✓ / ✗ / –"), h("th", {}, ""))), h("tbody", {}, list.map((a) => h("tr", {}, h("td", {}, h("a", { href: "#/result/" + a.id }, a.name)), h("td", { class: "muted" }, new Date(a.ts * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })), h("td", { class: "num" }, `${a.score} / ${a.maxscore}`), h("td", { class: "num" }, `${a.correct} / ${a.wrong} / ${a.skipped}`), h("td", { class: "num" }, h("span", { class: "pill " + (pct(a.correct, a.total) >= 60 ? "ok" : "bad") }, pct(a.correct, a.total) + "%")))))));
}

async function history(_arg, app) {
  const list = await api("/attempts/");
  app.replaceChildren(h("div", {}, h("h1", {}, "Test history"), recentTable(list)));
}

/* ---------- new test ---------- */
async function newTest(_arg, app) {
  const qstats = await api("/qstats/");
  const chS = {};
  for (const [qid, s] of Object.entries(qstats)) { const c = (chS[chapterOf(qid)] ||= { c: 0, w: 0 }); c.c += s.c; c.w += s.w; }
  const boxes = [];
  const view = h("div", {}, h("h1", {}, "Create a test"), h("p", { class: "muted" }, "Pick chapters (from any subjects), choose how many questions you want, and start."));
  for (const s of M.subjects) {
    const subjBox = h("input", { type: "checkbox", "aria-label": `Select all of ${s.name}` });
    const list = h("div", { class: "chlist" });
    const mine = [];
    let lastGroup = null;
    for (const ch of s.chapters) {
      if (ch.group && ch.group !== lastGroup) { list.append(h("div", { class: "grp" }, ch.group)); lastGroup = ch.group; }
      const cb = h("input", { type: "checkbox", value: ch.id });
      mine.push(cb); boxes.push(cb);
      const st = chS[ch.id];
      list.append(h("label", { class: "chk" }, cb, h("span", {}, ch.title), st && st.c + st.w ? h("span", { class: "pill " + (pct(st.c, st.c + st.w) >= 60 ? "ok" : "bad") }, pct(st.c, st.c + st.w) + "%") : null, h("span", { class: "cnt" }, ch.count)));
    }
    subjBox.onchange = () => mine.forEach((c) => (c.checked = subjBox.checked));
    const total = s.chapters.reduce((a, c) => a + c.count, 0);
    view.append(h("details", { class: "subj" }, h("summary", {}, h("label", { class: "chk", onclick: (e) => e.stopPropagation() }, subjBox, "All"), h("span", {}, s.name), h("span", { class: "sp" }), h("span", { class: "muted", style: "font-weight:500" }, `${s.chapters.length} chapters · ${nf(total)} questions`)), list));
  }
  const nQ = h("input", { type: "number", min: 1, max: 300, value: 20 });
  const mins = h("input", { type: "number", min: 0, max: 400, value: 20 });
  nQ.oninput = () => (mins.value = nQ.value);
  const neg = h("select", {}, h("option", { value: "0.33" }, "−0.33 (1/3, like BPSC/UPSC)"), h("option", { value: "0.25" }, "−0.25"), h("option", { value: "0" }, "No negative marking"));
  const src = h("select", {}, h("option", { value: "all" }, "Any question"), h("option", { value: "unseen" }, "Unseen first"), h("option", { value: "wrong" }, "Only questions I got wrong earlier"));
  const err = h("div", { class: "notice", style: "display:none" });
  const go = h("button", { class: "btn primary" }, "Start test");
  go.onclick = async () => {
    err.style.display = "none";
    const ids = boxes.filter((b) => b.checked).map((b) => b.value);
    if (!ids.length) { err.textContent = "Select at least one chapter."; err.style.display = ""; return; }
    go.disabled = true;
    try { await loadChapters(ids); } catch (e) { err.textContent = e.message; err.style.display = ""; go.disabled = false; return; }
    go.disabled = false;
    let pool = ids.flatMap((id) => qcache[id]);
    if (src.value === "wrong") pool = pool.filter((q) => qstats[q.id]?.last === "wrong");
    if (!pool.length) { err.textContent = "No questions match this filter in the selected chapters."; err.style.display = ""; return; }
    let order = shuffle(pool);
    if (src.value === "unseen") order = [...order.filter((q) => !qstats[q.id]), ...order.filter((q) => qstats[q.id])];
    const n = Math.min(+nQ.value || 20, order.length);
    const chosen = shuffle(order.slice(0, n));
    const subjectsIn = [...new Set(chosen.map((q) => subjectOf(q.id)))].map((id) => M.subjects.find((s) => s.id === id).name);
    startTest({ name: `${subjectsIn.length > 2 ? subjectsIn.length + " subjects" : subjectsIn.join(" + ")} · ${n}Q`, qids: chosen.map((q) => q.id), minutes: +mins.value || 0, marking: { correct: 1, negative: +neg.value } });
  };
  view.append(h("h2", {}, "Settings"), h("div", { class: "card" }, h("div", { class: "row" }, h("label", {}, "Questions ", nQ), h("label", {}, "Time (minutes, 0 = none) ", mins), h("label", {}, "Marking ", neg), h("label", {}, "Pick from ", src)), err, h("div", { style: "margin-top:14px" }, go)));
  app.replaceChildren(view);
}

/* ---------- running a test ---------- */
function startTest({ name, qids, minutes, marking }) {
  T = { name, qids, minutes, marking, idx: 0, answers: {}, startedAt: Date.now(), shownAt: Date.now() };
  saveT();
  location.hash = "#/test";
}

async function runTest(_arg, app) {
  if (!T) T = readActive();
  if (!T) { location.hash = "#/new"; return; }
  await loadChapters(T.qids.map(chapterOf));
  const qs = T.qids.map((id) => qmap[id]);
  T.shownAt = Date.now();
  const A = (id) => (T.answers[id] ||= { chosen: null, flagged: false, secs: 0 });
  const bank = (id) => { A(id).secs += (Date.now() - T.shownAt) / 1000; T.shownAt = Date.now(); };
  const go = (i) => { bank(qs[T.idx].id); T.idx = Math.max(0, Math.min(qs.length - 1, i)); saveT(); draw(); };

  const view = h("div", {});
  const timerEl = h("span", { class: "timer" });
  let submitting = false;
  const submit = async (auto) => {
    if (submitting) return;
    if (!auto) { const left = qs.filter((q) => !A(q.id).chosen).length; if (!confirm(left ? `${left} question(s) unanswered. Submit the test?` : "Submit the test?")) return; }
    submitting = true;
    bank(qs[T.idx].id);
    clearInterval(timerHandle);
    try {
      const res = await post("/attempts/", { name: T.name, duration: (Date.now() - T.startedAt) / 1000, config: { marking: T.marking, minutes: T.minutes }, answers: qs.map((q) => ({ qid: q.id, chosen: A(q.id).chosen, flagged: A(q.id).flagged, secs: A(q.id).secs })) });
      T = null; clearActive();
      location.hash = "#/result/" + res.id;
    } catch (e) {
      submitting = false;
      if (!T) return; // signed out meanwhile
      saveT(); // the answers stay on this device
      timerHandle = setInterval(tick, 1000);
      toast("Could not submit: " + e.message);
    }
  };
  const tick = () => {
    if (!T) return;
    if (!T.minutes) { timerEl.textContent = fmtTime((Date.now() - T.startedAt) / 1000); return; }
    const left = T.minutes * 60 - (Date.now() - T.startedAt) / 1000;
    timerEl.textContent = fmtTime(left); timerEl.classList.toggle("low", left < 60);
    if (left <= 0) { clearInterval(timerHandle); submit(true); }
  };

  function draw() {
    const q = qs[T.idx], a = A(q.id);
    const pal = h("div", { class: "pal" }, qs.map((x, i) => h("button", { class: [A(x.id).chosen ? "ans" : "", A(x.id).flagged ? "flag" : "", i === T.idx ? "cur" : ""].join(" "), "aria-label": `Question ${i + 1}`, onclick: () => go(i) }, i + 1)));
    const done = qs.filter((x) => A(x.id).chosen).length;
    const qv = questionView(q, { mode: "test", chosen: a.chosen, number: T.idx + 1, onPick: (l) => { a.chosen = l; saveT(); draw(); } });
    view.replaceChildren(
      h("div", { class: "testbar" }, h("b", {}, T.name), h("span", { class: "sp" }), timerEl, h("button", { class: "btn primary", onclick: () => submit(false) }, "Submit")),
      h("div", { class: "layout" },
        h("div", { class: "card" }, qv,
          h("div", { class: "row", style: "margin-top:16px" },
            h("button", { class: "btn", disabled: T.idx === 0, onclick: () => go(T.idx - 1) }, "← Previous"),
            h("button", { class: "btn", onclick: () => { a.flagged = !a.flagged; saveT(); draw(); } }, a.flagged ? "Unmark review" : "Mark for review"),
            h("button", { class: "btn", disabled: !a.chosen, onclick: () => { a.chosen = null; saveT(); draw(); } }, "Clear"),
            h("span", { class: "sp" }),
            h("button", { class: "btn primary", disabled: T.idx === qs.length - 1, onclick: () => go(T.idx + 1) }, "Next →"))),
        h("div", { class: "card" }, h("div", { class: "muted", style: "margin-bottom:8px;font-size:14px" }, `${done} of ${qs.length} answered`), pal,
          h("div", { class: "legend" }, h("span", {}, h("i", { style: "background:var(--ok-bg);border-color:var(--ok)" }), "Answered"), h("span", {}, h("i", { style: "background:var(--warn-bg);border-color:var(--warn)" }), "Marked"), h("span", {}, h("i", {}), "Not visited")),
          h("p", { class: "muted", style: "font-size:13px" }, "Keys: A–D choose · ←/→ move · M mark · C clear"))),
    );
    tick();
  }
  document.onkeydown = (e) => {
    if (location.hash !== "#/test" || !T || /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    const q = qs[T.idx], k = e.key.toLowerCase();
    if ("abcd".includes(k) && k.length === 1 && q.options.some((o) => o.label === k)) { A(q.id).chosen = k; saveT(); draw(); }
    else if (k === "arrowright" || k === "n") go(T.idx + 1);
    else if (k === "arrowleft" || k === "p") go(T.idx - 1);
    else if (k === "m") { A(q.id).flagged = !A(q.id).flagged; saveT(); draw(); }
    else if (k === "c") { A(q.id).chosen = null; saveT(); draw(); }
  };
  app.replaceChildren(view);
  draw();
  timerHandle = setInterval(tick, 1000);
}

/* ---------- result ---------- */
async function result(id, app) {
  const a = await api("/attempts/" + id + "/");
  await loadChapters(a.items.map((i) => chapterOf(i.qid)));
  const view = h("div", {});
  view.append(h("h1", {}, a.name),
    h("div", { class: "grid g4" },
      h("div", { class: "card stat" }, h("div", { class: "score" }, `${a.score}`), h("div", { class: "l" }, `of ${a.maxscore} marks`)),
      h("div", { class: "card stat" }, h("div", { class: "v" }, pct(a.correct, a.total) + "%"), h("div", { class: "l" }, "Accuracy")),
      h("div", { class: "card stat" }, h("div", { class: "v" }, `${a.correct} / ${a.wrong} / ${a.skipped}`), h("div", { class: "l" }, "Correct / Wrong / Skipped")),
      h("div", { class: "card stat" }, h("div", { class: "v" }, fmtTime(a.duration)), h("div", { class: "l" }, `Time taken · ${a.config.marking ? `−${a.config.marking.negative} per wrong` : ""}`))));

  const by = {};
  for (const i of a.items) { const c = (by[i.chapter] ||= { c: 0, w: 0, s: 0 }); c[i.status === "correct" ? "c" : i.status === "wrong" ? "w" : "s"]++; }
  view.append(h("h2", {}, "Chapter-wise result"), h("div", { class: "card", style: "overflow-x:auto" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Chapter"), h("th", { class: "num" }, "Correct"), h("th", { class: "num" }, "Wrong"), h("th", { class: "num" }, "Skipped"), h("th", { class: "num" }, "Accuracy"))), h("tbody", {}, Object.entries(by).map(([ch, c]) => h("tr", {}, h("td", {}, chTitle[ch] || ch), h("td", { class: "num" }, c.c), h("td", { class: "num" }, c.w), h("td", { class: "num" }, c.s), h("td", { class: "num" }, pct(c.c, c.c + c.w + c.s) + "%")))))));

  const weakIds = a.items.filter((i) => i.status !== "correct").map((i) => i.qid);
  view.append(h("div", { class: "row", style: "margin-top:16px" },
    h("button", { class: "btn primary", disabled: !weakIds.length, onclick: () => startTest({ name: "Retry · " + a.name, qids: shuffle(weakIds), minutes: 0, marking: a.config.marking || { correct: 1, negative: 0 } }) }, `Retry wrong + skipped (${weakIds.length})`),
    h("a", { class: "btn", href: "#/new" }, "New test"),
    h("button", { class: "btn danger", onclick: async () => { if (confirm("Delete this attempt from your history?")) { await api(`/attempts/${a.id}/`, { method: "DELETE" }); location.hash = "#/history"; } } }, "Delete")));

  view.append(h("h2", {}, "Review every question"));
  const listEl = h("div", {});
  const tabs = h("div", { class: "tabs" });
  let filter = "all";
  const draw = () => {
    tabs.replaceChildren(...[["all", "All"], ["wrong", "Wrong"], ["skipped", "Skipped"], ["correct", "Correct"]].map(([k, l]) => h("button", { class: filter === k ? "on" : "", onclick: () => { filter = k; draw(); } }, `${l} (${k === "all" ? a.items.length : a.items.filter((i) => i.status === k).length})`)));
    listEl.replaceChildren(...a.items.map((it, n) => ({ it, n })).filter(({ it }) => filter === "all" || it.status === filter).map(({ it, n }) => h("div", { class: "card rev" }, questionView(qmap[it.qid], { mode: "review", chosen: it.chosen || null, number: n + 1 }))));
    if (!listEl.children.length) listEl.append(h("p", { class: "muted" }, "Nothing here."));
  };
  view.append(tabs, listEl);
  draw();
  app.replaceChildren(view);
}

/* ---------- mistakes notebook ---------- */
async function mistakes(_arg, app) {
  const qstats = await api("/qstats/");
  const wrong = Object.entries(qstats).filter(([, s]) => s.last === "wrong").map(([id]) => id);
  const by = {};
  for (const id of wrong) (by[chapterOf(id)] ||= []).push(id);
  const view = h("div", {}, h("h1", {}, "Mistakes notebook"), h("p", { class: "muted" }, "Questions whose most recent attempt was wrong. Get one right in a later test and it leaves this list."));
  if (!wrong.length) view.append(h("div", { class: "card" }, "No mistakes recorded yet. Take a test and they will appear here."));
  else {
    view.append(h("div", { class: "row", style: "margin-bottom:12px" }, h("button", { class: "btn primary", onclick: () => startTest({ name: `Mistakes revision · ${Math.min(30, wrong.length)}Q`, qids: shuffle(wrong).slice(0, 30), minutes: 0, marking: { correct: 1, negative: 0.33 } }) }, `Practise mistakes (${Math.min(30, wrong.length)} of ${wrong.length})`)));
    view.append(h("div", { class: "card", style: "overflow-x:auto" }, h("table", {}, h("tbody", {}, Object.entries(by).map(([ch, ids]) => h("tr", {}, h("td", {}, chTitle[ch] || ch), h("td", { class: "num" }, ids.length + " wrong"), h("td", { class: "num" }, h("button", { class: "btn sm", onclick: () => startTest({ name: `Mistakes · ${chTitle[ch] || ch}`, qids: shuffle(ids), minutes: 0, marking: { correct: 1, negative: 0.33 } }) }, "Practise"))))))));
  }
  app.replaceChildren(view);
}

/* ============================== boot ============================== */
(async () => {
  try { ME = await api("/auth/me/"); } catch { ME = null; } // 401 just means "not signed in"
  if (!location.hash) location.hash = ME ? "#/dashboard" : "#/";
  route();
})();
