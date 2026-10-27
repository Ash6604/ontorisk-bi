"""Presentation layer for the dashboard: design tokens, global CSS/JS, HTML components, chart styling.

Nothing here touches data - app.py computes every number and passes it in, so all
figures shown are real values from the warehouse.
"""
from __future__ import annotations

import base64
import html

import streamlit as st

# ------------------------------------------------------------------ tokens
BG, S1, S2, S3 = "#000000", "#08090D", "#0D0F14", "#12141B"
BORDER, HAIRLINE = "#27272A", "#1C1E26"
TEXT, TEXT_2, MUTED = "#F8FAFC", "#A1A1AA", "#71717A"
VIOLET, CYAN, BLUE, EMERALD, MAGENTA, ROSE = "#8B5CF6", "#22D3EE", "#3B82F6", "#34D399", "#E879F9", "#FB7185"
FONT = "Geist, Inter, system-ui, sans-serif"
MONO = "'Geist Mono', ui-monospace, monospace"

# Categorical chart order, validated for CVD separation on the #0D0F14 card surface.
SERIES = ["#8B5CF6", "#0891B2", "#F43F5E", "#3B82F6", "#D97706", "#059669", "#D946EF", "#65A30D"]
PLOT_CONFIG = {"displayModeBar": False}

CSS = """
<style>
:root {
  --bg:#000; --s1:#08090D; --s2:#0D0F14; --s3:#12141B; --border:#27272A; --hair:#1C1E26;
  --text:#F8FAFC; --text2:#A1A1AA; --muted:#71717A;
  --violet:#8B5CF6; --cyan:#22D3EE; --blue:#3B82F6; --emerald:#34D399; --magenta:#E879F9; --rose:#FB7185;
  --r:14px; --ease:cubic-bezier(.2,.7,.2,1);
  --mono:'Geist Mono', ui-monospace, monospace;
}

/* ---------- canvas: pure black with a faint drifting haze */
.stApp { background:#000; }
.stApp::before {
  content:""; position:fixed; inset:-20%; pointer-events:none; z-index:0;
  background:
    radial-gradient(38% 30% at 18% 8%, rgba(139,92,246,.10), transparent 70%),
    radial-gradient(30% 26% at 88% 12%, rgba(34,211,238,.06), transparent 70%);
  animation: or-haze 36s ease-in-out infinite alternate;
}
@keyframes or-haze { to { transform: translate3d(3%, 2%, 0) scale(1.04); } }
[data-testid="stHeader"] { background: rgba(0,0,0,.55); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
                           border-bottom: 1px solid rgba(39,39,42,.5); }
[data-testid="stAppDeployButton"] { display:none; }
[data-testid="stMainBlockContainer"] { position:relative; z-index:1; padding: 2.4rem 2.5rem 5rem; max-width: 1480px; }
@media (max-width: 720px) { [data-testid="stMainBlockContainer"] { padding: 1.6rem 1rem 4rem; } }

/* ---------- motion */
@keyframes or-up { from { opacity:0; transform: translate3d(0,10px,0); } to { opacity:1; transform:none; } }
@keyframes or-fade { from { opacity:0; } to { opacity:1; } }
.or-enter { animation: or-up .5s var(--ease) both; animation-delay: calc(var(--i, 0) * 70ms); }
div[class*="st-key-card"], [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
  animation: or-up .55s var(--ease) both; animation-delay: .12s; }
[data-testid="stPlotlyChart"] { animation-name: or-fade; animation-delay: .2s; }

/* ---------- surfaces */
.or-card, div[class*="st-key-card"] {
  position:relative; background: linear-gradient(180deg, rgba(255,255,255,.018), transparent 40%), var(--s2);
  border: 1px solid var(--hair) !important; border-radius: var(--r) !important;
  box-shadow: 0 1px 0 rgba(255,255,255,.03) inset, 0 20px 40px -24px rgba(0,0,0,.9);
  transition: border-color .25s var(--ease), transform .25s var(--ease), box-shadow .25s var(--ease);
}
.or-card::after, div[class*="st-key-card"]::after {
  content:""; position:absolute; inset:0; border-radius:inherit; pointer-events:none; opacity:0;
  background: radial-gradient(420px circle at var(--mx, 50%) var(--my, 0%), rgba(139,92,246,.10), transparent 45%);
  transition: opacity .3s var(--ease);
}
.or-card:hover, div[class*="st-key-card"]:hover { border-color: #2E2A44 !important; }
.or-card:hover::after, div[class*="st-key-card"]:hover::after { opacity:1; }
div[class*="st-key-card"] { padding: 1.15rem 1.25rem 1rem !important; }

/* featured card: gradient hairline border */
div[class*="st-key-cardfeature"], .or-feature {
  border: 1px solid transparent !important;
  background:
    linear-gradient(var(--s2), var(--s2)) padding-box,
    linear-gradient(135deg, rgba(139,92,246,.75), rgba(34,211,238,.35) 45%, rgba(39,39,42,.6) 75%) border-box !important;
  box-shadow: 0 0 0 1px rgba(0,0,0,.4), 0 24px 60px -30px rgba(139,92,246,.45);
}

/* ---------- top bar */
.or-top { display:flex; align-items:flex-end; justify-content:space-between; gap:1.5rem; flex-wrap:wrap; }
.or-crumbs { display:flex; align-items:center; gap:.45rem; font-size:.78rem; color:var(--muted); margin:0 0 .55rem; }
.or-crumbs b { color:var(--text2); font-weight:500; }
.or-crumbs .ms { font-size:15px; }
.or-top h1 { font-size: clamp(1.6rem, 2.4vw, 2.15rem); font-weight:600; letter-spacing:-.03em; line-height:1.1;
             margin:0; padding:0; color:var(--text); }
.or-top p { color:var(--text2); margin:.5rem 0 0; max-width:64ch; line-height:1.55; font-size:.93rem; }
.or-status { display:inline-flex; white-space:nowrap; flex-wrap:nowrap; align-items:center; gap:.55rem; font-size:.78rem; color:var(--text2);
             padding:.42rem .75rem; border:1px solid var(--hair); border-radius:10px; background:rgba(13,15,20,.7); }
.or-status-wrap { display:flex; justify-content:flex-end; }
@media (max-width: 640px) { .or-status-wrap { justify-content:flex-start; } }
@media (max-width: 1180px) { .or-status .lbl, .or-status .lbl + .sep { display:none; } }
.or-status .dot { width:7px; height:7px; border-radius:50%; background:var(--emerald);
                  box-shadow:0 0 0 3px rgba(52,211,153,.15), 0 0 12px rgba(52,211,153,.6); }
.or-status .sep { width:1px; height:12px; background:var(--border); }
.or-status .num { font-family:var(--mono); color:var(--text); font-variant-numeric: tabular-nums; }

.or-scope { display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; font-size:.78rem; color:var(--muted); }
.or-scope .tag { display:inline-flex; align-items:center; gap:.35rem; color:var(--text2); background:var(--s2);
                 border:1px solid var(--hair); border-radius:8px; padding:.22rem .55rem; }
.or-scope .tag .ms { font-size:14px; color:var(--muted); }
.or-scope .tag.on { color:var(--text); border-color:rgba(139,92,246,.45); background:rgba(139,92,246,.08); }
.or-scope .tag.on .ms { color:var(--violet); }
.or-divider { height:1px; background:linear-gradient(90deg, var(--hair), transparent); margin:1.1rem 0 1.4rem; }

/* ---------- icons */
.ms { font-family:'Material Symbols Rounded'; font-weight:normal; font-style:normal; font-size:18px; line-height:1;
      letter-spacing:normal; text-transform:none; display:inline-block; white-space:nowrap; direction:ltr;
      -webkit-font-feature-settings:'liga'; font-feature-settings:'liga'; -webkit-font-smoothing:antialiased;
      font-variation-settings:'wght' 400, 'FILL' 0; vertical-align:middle; }

/* ---------- KPI cards */
.or-kpis { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 14px; }
@media (max-width: 1100px) { .or-kpis { grid-template-columns: repeat(2, minmax(0,1fr)); } }
@media (max-width: 560px)  { .or-kpis { grid-template-columns: 1fr; } }
.or-kpi { padding: 1.05rem 1.15rem 0; overflow:hidden; display:flex; flex-direction:column; min-height: 168px; }
.or-kpi header { display:flex; align-items:center; gap:.6rem; color:var(--text2); font-size:.82rem; font-weight:500; }
.or-kpi .ico { width:28px; height:28px; border-radius:8px; display:grid; place-items:center; color:var(--accent);
               background: color-mix(in srgb, var(--accent) 12%, transparent);
               box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 28%, transparent); }
.or-kpi .ico .ms { font-size:17px; }
.or-kpi .val { margin-top:.85rem; font-size: 2.1rem; font-weight:600; letter-spacing:-.035em; line-height:1;
               color:var(--text); font-variant-numeric: tabular-nums; }
.or-kpi .val small { font-size:.95rem; color:var(--muted); font-weight:500; letter-spacing:0; margin-left:.25rem; }
.or-kpi .foot { display:flex; align-items:center; gap:.5rem; margin-top:.6rem; font-size:.76rem; color:var(--muted); }
.or-trend { display:inline-flex; align-items:center; gap:.15rem; font-weight:600; font-variant-numeric: tabular-nums;
            padding:.1rem .38rem; border-radius:6px; font-size:.74rem; }
.or-trend .ms { font-size:14px; }
.or-trend.bad  { color:var(--rose);    background:rgba(251,113,133,.10); }
.or-trend.good { color:var(--emerald); background:rgba(52,211,153,.10); }
.or-trend.flat { color:var(--text2);   background:rgba(161,161,170,.10); }
.or-spark { display:block; width:calc(100% + 2.3rem); height:56px; margin: auto -1.15rem 0; }
.or-kpi .bar-track { margin: auto 0 1.1rem; height:6px; border-radius:6px; background:var(--s3); overflow:hidden; }
.or-kpi .bar-fill { height:100%; border-radius:inherit; transform-origin:left;
                    background:linear-gradient(90deg, var(--violet), var(--cyan));
                    box-shadow:0 0 14px rgba(34,211,238,.45); animation: or-grow 1s var(--ease) .3s both; }
@keyframes or-grow { from { transform: scaleX(0); } }

/* tooltips */
.or-tip { position:relative; display:inline-grid; place-items:center; color:var(--muted); cursor:help; outline:none;
          border-radius:6px; }
.or-tip .ms { font-size:15px; }
.or-tip::after { content:attr(data-tip); position:absolute; left:50%; bottom:calc(100% + 8px); width:max-content; max-width:240px;
                 transform:translate(-50%, 4px); opacity:0; pointer-events:none; z-index:20;
                 background:rgba(18,20,27,.96); backdrop-filter:blur(8px); color:var(--text); border:1px solid var(--border);
                 padding:.5rem .65rem; border-radius:8px; font-size:.75rem; font-weight:400; line-height:1.45;
                 box-shadow:0 12px 30px -10px rgba(0,0,0,.9); transition: opacity .18s var(--ease), transform .18s var(--ease); }
.or-tip:hover::after, .or-tip:focus-visible::after { opacity:1; transform:translate(-50%, 0); }
.or-tip:focus-visible { box-shadow:0 0 0 2px var(--violet); }

/* ---------- card headings */
.or-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; margin-bottom:.15rem; }
.or-head h3 { font-size:.98rem; font-weight:600; letter-spacing:-.01em; color:var(--text); margin:0; padding:0;
              display:flex; align-items:center; gap:.5rem; }
.or-head h3 .ms { color:var(--violet); font-size:18px; }
.or-head p { color:var(--muted); font-size:.8rem; margin:.25rem 0 0; }
.or-badge { font-size:.72rem; color:var(--text2); border:1px solid var(--border); border-radius:6px; padding:.12rem .45rem;
            font-family:var(--mono); white-space:nowrap; }

/* ---------- featured rule */
.or-rule .eyebrow { display:flex; align-items:center; gap:.45rem; font-size:.72rem; font-weight:600; letter-spacing:.08em;
                    text-transform:uppercase; color:var(--cyan); }
.or-rule .eyebrow .ms { font-size:16px; }
.or-rule .stmt { color:var(--text); font-size:1.02rem; line-height:1.6; margin:.8rem 0 1rem; letter-spacing:-.005em; }
.or-chip { display:inline-block; font-family:var(--mono); font-size:.8rem; color:#DDD6FE; padding:.05rem .4rem;
           border-radius:6px; background:rgba(139,92,246,.12); border:1px solid rgba(139,92,246,.25); margin:.1rem 0; }
.or-chip.then { color:#A5F3FC; background:rgba(34,211,238,.09); border-color:rgba(34,211,238,.25); }
.or-stats { display:grid; grid-template-columns: repeat(3, 1fr); border-top:1px solid var(--hair); }
.or-stats div { padding:.8rem 0 .1rem; }
.or-stats div + div { padding-left:1rem; border-left:1px solid var(--hair); }
.or-stats dt { font-size:.72rem; color:var(--muted); }
.or-stats dd { margin:.2rem 0 0; font-size:1.25rem; font-weight:600; letter-spacing:-.02em; color:var(--text);
               font-variant-numeric: tabular-nums; }

/* ---------- lists (clusters / risk mix) */
.or-list { display:grid; }
.or-row { display:grid; grid-template-columns: 10px 1fr auto; gap:.75rem; align-items:center; padding:.72rem .2rem;
          border-bottom:1px solid var(--hair); border-radius:8px; transition: background .2s var(--ease); }
.or-row:last-child { border-bottom:0; }
.or-row:hover { background:rgba(255,255,255,.02); }
.or-row i { width:10px; height:10px; border-radius:3px; box-shadow:0 0 10px var(--c); background:var(--c); }
.or-row .n { color:var(--text); font-size:.86rem; font-weight:500; }
.or-row .d { color:var(--muted); font-size:.76rem; margin-top:.15rem; }
.or-row .v { text-align:right; font-variant-numeric: tabular-nums; color:var(--text); font-weight:600; font-size:.92rem; }
.or-row .v span { display:block; color:var(--muted); font-weight:400; font-size:.72rem; }
.or-meter { height:4px; border-radius:4px; background:var(--s3); margin-top:.45rem; overflow:hidden; }
.or-meter b { display:block; height:100%; border-radius:inherit; background:var(--c); transform-origin:left;
              animation: or-grow .9s var(--ease) .2s both; }

/* ---------- empty state */
.or-empty { text-align:center; padding:2.6rem 1rem; border:1px dashed var(--border); border-radius:var(--r);
            background: radial-gradient(60% 80% at 50% 0%, rgba(139,92,246,.07), transparent 70%), var(--s1); }
.or-empty .ms { font-size:28px; color:var(--violet); width:52px; height:52px; display:inline-grid; place-items:center;
                border-radius:14px; background:rgba(139,92,246,.1); box-shadow: inset 0 0 0 1px rgba(139,92,246,.25); }
.or-empty h4 { color:var(--text); font-size:1rem; font-weight:600; margin:.9rem 0 .3rem; padding:0; }
.or-empty p { color:var(--muted); font-size:.85rem; margin:0 auto; max-width:46ch; }

/* ---------- sidebar */
[data-testid="stSidebar"] { background:
    radial-gradient(120% 40% at 0% 0%, rgba(139,92,246,.07), transparent 60%), #08090D; }
[data-testid="stSidebarHeader"] { padding-bottom: .4rem; }
[data-testid="stSidebarNav"] { padding-top:.25rem; }
[data-testid="stSidebarNavLink"] { position:relative; border-radius:9px; margin:1px .35rem; padding:.42rem .7rem;
                                   transition: background .2s var(--ease), color .2s var(--ease); }
[data-testid="stSidebarNavLink"] span { color:var(--text2); font-weight:500; transition: color .2s var(--ease); }
[data-testid="stSidebarNavLink"]:hover { background:rgba(255,255,255,.035); }
[data-testid="stSidebarNavLink"]:hover span { color:var(--text); }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: linear-gradient(90deg, rgba(139,92,246,.16), rgba(139,92,246,.03)); }
[data-testid="stSidebarNavLink"][aria-current="page"] span { color:var(--text); }
[data-testid="stSidebarNavLink"][aria-current="page"]::before {
  content:""; position:absolute; left:-.35rem; top:22%; bottom:22%; width:3px; border-radius:0 3px 3px 0;
  background:linear-gradient(var(--violet), var(--cyan)); box-shadow:0 0 12px rgba(139,92,246,.8); }
[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] { color:var(--violet); }
[data-testid="stSidebarNavSeparator"] { border-color: var(--hair); }
.or-side-label { display:flex; align-items:center; gap:.4rem; font-size:.68rem; font-weight:600; letter-spacing:.1em;
                 text-transform:uppercase; color:var(--muted); margin:.4rem 0 -.2rem; }
.or-side-label .ms { font-size:14px; }
.or-side-foot { font-size:.74rem; color:var(--muted); line-height:1.6; border-top:1px solid var(--hair);
                padding-top:.9rem; margin-top:.6rem; }
.or-side-foot b { color:var(--text2); font-weight:500; }

/* ---------- native widgets */
[data-baseweb="select"] > div, [data-testid="stTextInputRootElement"], [data-testid="stDateInputField"],
[data-baseweb="textarea"] {
  background: var(--s2) !important; border-color: var(--hair) !important;
  transition: border-color .2s var(--ease), box-shadow .2s var(--ease); }
[data-baseweb="select"] > div:hover, [data-testid="stTextInputRootElement"]:hover, [data-baseweb="textarea"]:hover {
  border-color:#34343A !important; }
[data-baseweb="select"] > div:focus-within, [data-testid="stTextInputRootElement"]:focus-within,
[data-baseweb="textarea"]:focus-within {
  border-color: rgba(139,92,246,.7) !important; box-shadow: 0 0 0 3px rgba(139,92,246,.18) !important; }
[data-baseweb="tag"] { background: rgba(139,92,246,.16) !important; border:1px solid rgba(139,92,246,.35); }
[data-baseweb="tag"] span { color:#E9E3FF !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: rgba(13,15,20,.97) !important; backdrop-filter: blur(12px); }
[data-baseweb="popover"] > div { animation: or-up .18s var(--ease) both; }
textarea { font-family: var(--mono) !important; font-size:.84rem !important; line-height:1.6 !important; }
[data-testid="stWidgetLabel"] p { color: var(--text2); font-weight:500; font-size:.8rem; }

[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #8B5CF6, #6D5AF6 45%, #3B82F6) !important; border:0 !important;
  box-shadow: 0 0 0 1px rgba(139,92,246,.5), 0 8px 24px -8px rgba(139,92,246,.7), inset 0 1px 0 rgba(255,255,255,.18);
  transition: transform .18s var(--ease), box-shadow .25s var(--ease), filter .2s var(--ease); }
[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.12);
  box-shadow: 0 0 0 1px rgba(139,92,246,.7), 0 12px 32px -8px rgba(139,92,246,.85), inset 0 1px 0 rgba(255,255,255,.2); }
[data-testid="stBaseButton-primary"]:active { transform: translateY(1px) scale(.985); }
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-tertiary"] { transition: all .2s var(--ease); }
[data-testid="stBaseButton-secondary"]:hover { border-color: rgba(139,92,246,.6) !important; color: var(--text) !important; }

/* segmented controls */
[data-testid="stButtonGroup"] button { background: var(--s1); border-color: var(--hair); color: var(--text2);
                                       transition: all .2s var(--ease); }
[data-testid="stButtonGroup"] button:hover { color: var(--text); border-color:#34343A; }
[data-testid="stButtonGroup"] button[kind*="Active"], [data-testid="stButtonGroup"] button[aria-checked="true"] {
  background: rgba(139,92,246,.16) !important; border-color: rgba(139,92,246,.55) !important; color: #EDE9FE !important; }

/* sliders */
[data-testid="stSlider"] [role="slider"] { box-shadow: 0 0 0 4px rgba(139,92,246,.2), 0 0 14px rgba(139,92,246,.6); }

/* page links */
[data-testid="stPageLink"] a { border-radius:8px; transition: background .2s var(--ease); }
[data-testid="stPageLink"] a:hover { background: rgba(139,92,246,.1); }
[data-testid="stPageLink"] span { color: var(--cyan) !important; }

*:focus-visible { outline: 2px solid var(--violet) !important; outline-offset: 2px; }

/* scrollbars */
* { scrollbar-width: thin; scrollbar-color: #27272A transparent; }
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background:#1F2027; border-radius:10px; border:3px solid #000; }
::-webkit-scrollbar-thumb:hover { background:#34343A; }

[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stCaptionContainer"] { color: var(--muted); }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .001ms !important; animation-delay: 0s !important;
                           transition-duration: .001ms !important; }
  .stApp::before { animation: none; }
}
</style>
"""

JS = """
<script>
(() => {
  if (window.__orInit) { window.__orScan && window.__orScan(); return; }
  window.__orInit = true;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const last = {};
  const fmt = (v, d) => v.toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
  const count = el => {
    if (el.__orDone) return;
    el.__orDone = true;
    const to = parseFloat(el.dataset.value), d = parseInt(el.dataset.decimals || '0', 10), key = el.dataset.key;
    const from = key in last ? last[key] : 0;
    last[key] = to;
    if (reduce || from === to || !isFinite(to)) { el.textContent = fmt(to, d); return; }
    const t0 = performance.now(), dur = 950;
    const step = now => {
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 4);
      el.textContent = fmt(from + (to - from) * e, d);
      if (p < 1) requestAnimationFrame(step);
    };
    el.textContent = fmt(from, d);
    requestAnimationFrame(step);
  };
  const scan = window.__orScan = () => document.querySelectorAll('[data-countup]').forEach(count);
  new MutationObserver(scan).observe(document.body, {childList: true, subtree: true});
  scan();
  // cursor-following light on cards
  document.addEventListener('pointermove', e => {
    const card = e.target.closest && e.target.closest('.or-card, [class*="st-key-card"]');
    if (!card) return;
    const r = card.getBoundingClientRect();
    card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    card.style.setProperty('--my', (e.clientY - r.top) + 'px');
  }, {passive: true});
})();
</script>
"""


def inject():
    st.html(CSS)
    st.html(JS, unsafe_allow_javascript=True)


def esc(s) -> str:
    return html.escape(str(s))


def icon(name: str) -> str:
    return f'<span class="ms" aria-hidden="true">{name}</span>'


def tip(text: str) -> str:
    return f'<span class="or-tip" tabindex="0" role="note" aria-label="{esc(text)}" data-tip="{esc(text)}">{icon("info")}</span>'


# ------------------------------------------------------------------ page chrome
def topbar(page: str, title: str, subtitle: str):
    st.html(f"""
    <header class="or-top">
      <div class="or-enter" style="--i:0">
        <nav class="or-crumbs" aria-label="Breadcrumb">{icon("radar")} OntoRisk BI {icon("chevron_right")}
          <b>{esc(page)}</b></nav>
        <h1>{esc(title)}</h1>
        <p>{esc(subtitle)}</p>
      </div>
    </header>""")


def status_pill(events: int, built: str):
    st.html(f'<div class="or-status-wrap"><div class="or-status or-enter" style="--i:1" role="status"'
            f' title="DuckDB warehouse online"><span class="dot"></span><span class="lbl">Online</span>'
            f'<span class="sep"></span><span><span class="num">{events:,}</span> events</span>'
            f'<span class="sep"></span><span>built <span class="num">{esc(built)}</span></span></div></div>')


def scope_tags(tags: list[tuple[str, str, bool]]):
    """tags: (icon, text, active?) - active ones are filters the user has narrowed."""
    body = "".join(f'<span class="tag{" on" if on else ""}">{icon(ic)}{esc(t)}</span>' for ic, t, on in tags)
    st.html(f'<div class="or-scope or-enter" style="--i:2">{body}</div>')


def divider():
    st.html('<div class="or-divider"></div>')


def card_head(title: str, sub: str = "", ico: str = "", badge: str = ""):
    st.html(f"""<div class="or-head"><div><h3>{icon(ico) if ico else ""}{esc(title)}</h3>
      {f"<p>{esc(sub)}</p>" if sub else ""}</div>{f'<span class="or-badge">{esc(badge)}</span>' if badge else ""}</div>""")


def empty_state(ico: str, title: str, body: str):
    st.html(f'<div class="or-empty or-enter">{icon(ico)}<h4>{esc(title)}</h4><p>{esc(body)}</p></div>')


# ------------------------------------------------------------------ KPI cards
def sparkline(values, color: str) -> str:
    """Area sparkline as a self-contained SVG image (st.html strips inline <svg>); draws itself in on load."""
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    w, h, pad = 400.0, 56.0, 6.0
    pts = [(i * w / (len(vals) - 1), pad + (h - 2 * pad) * (1 - (v - lo) / span)) for i, v in enumerate(vals)]
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none">
      <style>
        .l {{ fill:none; stroke:{color}; stroke-width:1.75; stroke-linecap:round; stroke-linejoin:round;
              stroke-dasharray:1; stroke-dashoffset:1; animation:d 1.2s cubic-bezier(.2,.7,.2,1) .3s forwards; }}
        .a {{ opacity:0; animation:f .9s ease .6s forwards; }}
        @keyframes d {{ to {{ stroke-dashoffset:0; }} }} @keyframes f {{ to {{ opacity:1; }} }}
        @media (prefers-reduced-motion: reduce) {{ .l {{ animation:none; stroke-dashoffset:0; }} .a {{ animation:none; opacity:1; }} }}
      </style>
      <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{color}" stop-opacity=".34"/><stop offset="1" stop-color="{color}" stop-opacity="0"/>
      </linearGradient></defs>
      <path class="a" d="{line} L{w:.0f},{h:.0f} L0,{h:.0f} Z" fill="url(#g)"/>
      <path class="l" d="{line}" pathLength="1"/></svg>"""
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<img class="or-spark" src="{uri}" alt="" aria-hidden="true">'


def trend_badge(pct: float | None, higher_is_bad: bool = True) -> str:
    if pct is None:
        return ""
    if abs(pct) < 0.005:
        return f'<span class="or-trend flat">{icon("trending_flat")}0%</span>'
    bad = (pct > 0) == higher_is_bad
    return (f'<span class="or-trend {"bad" if bad else "good"}">'
            f'{icon("trending_up" if pct > 0 else "trending_down")}{abs(pct):.0%}</span>')


def kpi_cards(cards: list[dict]):
    """Each card: label, value, decimals, key, icon, accent, note, [unit, help, trend, spark, progress]."""
    out = []
    for i, c in enumerate(cards):
        value = c["value"]
        shown = "—" if value is None else f"{value:,.{c.get('decimals', 0)}f}"
        num = (f'<span data-countup data-key="{c["key"]}" data-value="{value}" data-decimals="{c.get("decimals", 0)}">'
               f'{shown}</span>') if value is not None else shown
        bottom = ""
        if c.get("spark") is not None:
            bottom = sparkline(c["spark"], c["accent"])
        elif c.get("progress") is not None:
            bottom = (f'<div class="bar-track" role="presentation"><div class="bar-fill" '
                      f'style="width:{max(0.0, min(1.0, c["progress"])) * 100:.1f}%"></div></div>')
        out.append(f"""
        <article class="or-card or-kpi or-enter" style="--i:{i + 2};--accent:{c['accent']}" aria-label="{esc(c['label'])}">
          <header><span class="ico">{icon(c['icon'])}</span><span>{esc(c['label'])}</span>
            {tip(c['help']) if c.get('help') else ''}</header>
          <div class="val">{num}{f"<small>{esc(c['unit'])}</small>" if c.get('unit') else ''}</div>
          <div class="foot">{c.get('trend', '')}<span>{esc(c.get('note', ''))}</span></div>
          {bottom}
        </article>""")
    st.html(f'<section class="or-kpis" aria-label="Key metrics">{"".join(out)}</section>')


# ------------------------------------------------------------------ feature + list blocks
def rule_feature(when: list[str], then: list[str], confidence: float, lift: float, support: float, label: str):
    w = " and ".join(f'<span class="or-chip">{esc(x)}</span>' for x in when)
    t = " and ".join(f'<span class="or-chip then">{esc(x)}</span>' for x in then)
    st.html(f"""<div class="or-rule">
      <div class="eyebrow">{icon("bolt")}{esc(label)}</div>
      <p class="stmt">When {w}, the event is {t} in <b>{confidence:.0%}</b> of cases.</p>
      <dl class="or-stats">
        <div><dt>Confidence</dt><dd>{confidence:.0%}</dd></div>
        <div><dt>Lift</dt><dd>{lift:.2f}×</dd></div>
        <div><dt>Support</dt><dd>{support:.0%}</dd></div>
      </dl></div>""")


def rows(items: list[dict]):
    """items: name, desc, value, value_label, color, [share 0..1]."""
    body = "".join(f"""<div class="or-row" style="--c:{it['color']}"><i></i>
        <div><div class="n">{esc(it['name'])}</div><div class="d">{esc(it['desc'])}</div>
          {f'<div class="or-meter"><b style="width:{it["share"] * 100:.1f}%"></b></div>' if it.get('share') is not None else ''}
        </div>
        <div class="v">{esc(it['value'])}<span>{esc(it['value_label'])}</span></div></div>""" for it in items)
    st.html(f'<div class="or-list">{body}</div>')


# ------------------------------------------------------------------ charts
def style(fig, height: int, legend: bool = True):
    """Dark chart style: hairline y-grid only, legend above the plot, glassy tooltips, eased data transitions."""
    fig.update_layout(
        template="none", height=height, font=dict(family=FONT, size=12, color=TEXT_2),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=4, r=8, t=34 if legend else 8, b=4), showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="", font=dict(size=12, color=TEXT_2),
                    itemsizing="constant", bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="rgba(18,20,27,0.96)", bordercolor=BORDER, font=dict(family=FONT, size=12, color=TEXT)),
        hovermode="closest", bargap=0.32, transition=dict(duration=400, easing="cubic-in-out"))
    fig.update_xaxes(automargin=True, showgrid=False, zeroline=False, linecolor=HAIRLINE, ticks="", ticklen=0,
                     title_font=dict(size=12, color=MUTED), tickfont=dict(color=MUTED))
    fig.update_yaxes(automargin=True, gridcolor="#16181F", zeroline=False, showline=False,
                     title_font=dict(size=12, color=MUTED), tickfont=dict(color=MUTED))
    return fig
