"""styles.py — global CSS for TruthLens. Keep customization additive & simple.

"""

CUSTOM_CSS = """
<style>
:root{
    --tl-rose:#be185d;
    --tl-rose-dark:#9d174d;
    --tl-rose-light:#fdf2f8;
    --tl-rose-border:#fbcfe8;
    --tl-teal:#0d9488;
    --tl-teal-dark:#0f766e;
    --tl-border:#f1e3dd;
    --tl-real:#b45309;
    --tl-uncertain:#db2777;
    --tl-misinfo:#be123c;
    --tl-muted:#78716c;
}

/* Base */
.stApp { background-color: #fdf6f3; }
h1, h2, h3, h4 { color: var(--tl-rose-dark); font-family: 'Segoe UI', 'Inter', sans-serif; }
[data-testid="stSidebar"]{
    background-color: var(--tl-rose-light);
    border-right: 1px solid var(--tl-rose-border);
}
[data-testid="stSidebar"] * { color: #9d174d !important; }
[data-testid="stSidebar"] .tl-brand-title{
    font-size:1.35rem; font-weight:800; color:#be185d !important; letter-spacing:0.5px;
}
[data-testid="stSidebar"] .tl-brand-sub{ font-size:0.78rem; color:#c2417c !important; margin-bottom:0.6rem;}
[data-testid="stSidebar"] .tl-nav-section{
    font-size:0.68rem; letter-spacing:1.2px; color:#c2417c !important;
    text-transform:uppercase; margin:1rem 0 0.3rem 0; font-weight:700;
}
[data-testid="stSidebar"] .tl-footer{
    font-size:0.72rem; color:#c2417c !important; border-top:1px solid var(--tl-rose-border); margin-top:1rem; padding-top:0.7rem;
}

/* Cards */
.tl-card{
    background:#ffffff !important; border:none !important; border-radius:12px;
    padding:1.1rem 1.3rem; margin-bottom:0.9rem; box-shadow:0 1px 2px rgba(41,37,36,0.05);
}
.tl-card-title{ font-size:0.78rem; text-transform:uppercase; letter-spacing:0.8px;
    color:var(--tl-muted); font-weight:700; margin-bottom:0.4rem;}

/* Verdict banner */
.tl-verdict{
    border-radius:14px; padding:1.3rem 1.5rem; margin-bottom:1rem; color:#fff;
}
.tl-verdict-real{ background:linear-gradient(135deg,#854d0e,#ca8a04); }
.tl-verdict-uncertain{ background:linear-gradient(135deg,#9d174d,#db2777); }
.tl-verdict-misinfo{ background:linear-gradient(135deg,#9f1239,#be123c); }
.tl-verdict-label{ font-size:1.35rem; font-weight:800; letter-spacing:0.3px;}
.tl-verdict-sub{ font-size:0.85rem; opacity:0.92; margin-top:0.15rem;}

/* Badges */
.tl-badge{ display:inline-block; padding:0.18rem 0.65rem; border-radius:999px;
    font-size:0.74rem; font-weight:700; letter-spacing:0.2px;}
.tl-badge-high{ background:#fee2e2; color:#b91c1c; }
.tl-badge-medium{ background:#fce7f3; color:#be185d; }
.tl-badge-low{ background:#fef9c3; color:#a16207; }
.tl-badge-pending{ background:#fef9c3; color:#a16207; }
.tl-badge-confirmed{ background:#fef3c7; color:#92400e; }
.tl-badge-dismissed{ background:#f1ede9; color:#78716c; }
.tl-badge-relabeled{ background:#ccfbf1; color:#0f766e; }
.tl-badge-real{ background:#fef3c7; color:#92400e; }
.tl-badge-uncertain{ background:#fce7f3; color:#be185d; }
.tl-badge-misinfo{ background:#fee2e2; color:#b91c1c; }

/* Progress bars */
.tl-bar-track{ background:#e7e2df; border-radius:999px; height:10px; width:100%; overflow:hidden;}
.tl-bar-fill{ height:10px; border-radius:999px; }

/* Header */
.tl-header{ padding-bottom:0.4rem; border-bottom:1px solid var(--tl-border); margin-bottom:1.1rem;}

/* Persistent top masthead (main area, visible even when sidebar is collapsed) */
.tl-masthead{
    display:flex; align-items:baseline; gap:0.6rem;
    padding:0.2rem 0 0.9rem 0; border-bottom:1px solid var(--tl-border); margin-bottom:1rem;
}
.tl-masthead-brand{ font-size:1.3rem; font-weight:800; color:var(--tl-rose-dark); letter-spacing:0.6px; }
.tl-masthead-sub{ font-size:0.82rem; color:var(--tl-muted); }

/* All buttons: always teal and clearly visible, everywhere (including sidebar) */
.stButton > button, .stButton > button:focus, .stButton > button:focus:not(:active){
    background-color:#0d9488 !important;
    color:#ffffff !important;
    border:none !important;
    width:100% !important;
}
.stButton > button:hover{
    background-color:#0f766e !important;
    border:none !important;
    color:#ffffff !important;
}
.stButton > button:active{
    background-color:#115e59 !important;
    border:none !important;
    color:#ffffff !important;
}

/* Sidebar nav buttons: a contrasting gold accent against the sidebar's light rose background. */
div[class*="st-key-navbtn_"][class*="_active"] .stButton > button,
div[class*="st-key-navbtn_"][class*="_active"] .stButton > button:hover{
    background-color:#b45309 !important;
    border:none !important;
    color:#ffffff !important;
    width:100% !important;
}
div[class*="st-key-navbtn_"][class*="_inactive"] .stButton > button{
    background-color:#fde68a !important;
    border:2px solid #fbbf24 !important;
    color:#92400e !important;
    width:100% !important;
}
div[class*="st-key-navbtn_"][class*="_inactive"] .stButton > button:hover{
    background-color:#fcd34d !important;
    border:2px solid #b45309 !important;
    color:#92400e !important;
    width:100% !important;
}

/* Review Queue case card: two-column layout — identity on the left,
   review status/verdict information on the right, split by a subtle divider. */
div[class*="st-key-case_card_"]{
    background:#ffffff; border:1px solid var(--tl-border); border-radius:12px;
    padding:1.1rem 1.3rem 0.9rem 1.3rem; margin-bottom:0.9rem;
    box-shadow:0 1px 2px rgba(41,37,36,0.05);
}
div[class*="st-key-case_card_"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-of-type{
    border-right:1px solid var(--tl-border);
    padding-right:1.2rem;
}
div[class*="st-key-case_card_"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-of-type{
    padding-left:1.2rem;
}
.tl-case-id{ font-size:0.74rem; font-weight:700; letter-spacing:0.3px; color:var(--tl-muted); margin-bottom:0.3rem; }
.tl-case-title{ font-size:1.06rem; font-weight:800; line-height:1.4; color:#1c1917; margin-bottom:0.5rem; }
.tl-case-source{ font-size:0.82rem; color:var(--tl-muted); }
.tl-case-right-row{ margin-bottom:0.5rem; }
.tl-case-right-row:last-child{ margin-bottom:0; }
.tl-case-confidence{ font-size:0.86rem; color:#44403c; font-weight:600; }
.tl-case-time{ font-size:0.8rem; color:var(--tl-muted); margin-left:0.3rem; }

/* "View Case" action: bottom-right of the right-hand section */
div[class*="st-key-case_viewbtn_"]{ display:flex; justify-content:flex-end; margin-top:0.6rem; }
div[class*="st-key-case_viewbtn_"] .stButton > button{
    padding:0.35rem 0.95rem; font-size:0.82rem;
}

/* Highlight legend */
.tl-hl-semantic{ background:#fef08a; padding:0.05rem 0.2rem; border-radius:4px;}
.tl-hl-linguistic{ background:#99f6e4; padding:0.05rem 0.2rem; border-radius:4px;}
.tl-hl-claim{ background:#fbcfe8; padding:0.05rem 0.2rem; border-radius:4px;}

/* Empty state */
.tl-empty{ text-align:center; padding:2.4rem 1rem; color:var(--tl-muted); }

/* Timeline */
.tl-timeline-item{ border-left:2px solid var(--tl-border); padding-left:0.9rem; margin-left:0.4rem;
    padding-bottom:0.7rem; }
.tl-timeline-time{ font-size:0.72rem; color:var(--tl-muted); font-weight:600;}

/* Section note */
.tl-note{ font-size:0.82rem; color:var(--tl-muted); font-style:italic; }

/* Prototype tag */
.tl-proto-tag{ display:inline-block; background:#fdf2f8; color:#be185d; font-size:0.7rem;
    font-weight:700; padding:0.15rem 0.55rem; border-radius:6px; letter-spacing:0.3px;}

/* Buttons: make every inner element (label, emoji, text wrapper) transparent so the
   button colour fills the whole button — the global light-theme rule below would
   otherwise paint a pale patch behind the label. */
.stButton > button *,
.stDownloadButton > button *,
[data-testid="stSidebar"] .stButton > button *{
    background:transparent !important;
    background-color:transparent !important;
}
.stButton > button, .stButton > button *,
.stDownloadButton > button, .stDownloadButton > button *{ color:#ffffff !important; }
.stDownloadButton > button{ background-color:#0d9488 !important; border:none !important; width:100% !important; }
.stDownloadButton > button:hover{ background-color:#0f766e !important; }
div[class*="st-key-navbtn_"][class*="_inactive"] .stButton > button,
div[class*="st-key-navbtn_"][class*="_inactive"] .stButton > button *{ color:#78350f !important; }
div[class*="st-key-navbtn_"][class*="_active"] .stButton > button,
div[class*="st-key-navbtn_"][class*="_active"] .stButton > button *{ color:#ffffff !important; }

/* Force light theme and readable text */
body, .stApp, [class*="st"] {
    background-color: #fdf6f3 !important;
    color: #262730 !important;
}
p, div, span, label, button, input, textarea, select {
    color: #262730 !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {
    background-color: #ffffff !important;
    color: #262730 !important;
    border-color: #e7e2df !important;
}
</style>
"""
