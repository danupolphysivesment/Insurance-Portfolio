"""MTL-inspired pink theme: palette, CSS, and shared Plotly styling."""

# ---------- palette (Muang Thai Life-style magenta/pink) ----------
PRIMARY = "#E6007E"        # MTL magenta-pink
PRIMARY_DARK = "#A3005A"
PRIMARY_LIGHT = "#FF6EB4"
ACCENT_GOLD = "#C9932F"    # warm accent for "recommended" badges
BG = "#FFF7FB"             # near-white, pink-tinted page background
CARD = "#FFFFFF"
CARD_HI = "#FDEAF3"        # soft pink card fill for highlighted rows
BORDER = "#F4CBE0"
TEXT = "#2B1223"
TEXT_DIM = "#7A5468"
GOOD = "#1A8754"
WARN = "#B8860B"
BAD = "#C0392B"

CATEGORY_COLORS = {
    "health": "#E6007E",
    "investment": "#8E44AD",
    "life": "#2E86AB",
    "retirement": "#C9932F",
}

CATEGORY_LABELS_TH = {
    "health": "ประกันสุขภาพ",
    "investment": "ประกันควบการลงทุน",
    "life": "ประกันชีวิต",
    "retirement": "ประกันบำนาญ",
}

PLOTLY_FONT = "Sarabun, 'Trebuchet MS', sans-serif"

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Sarabun', 'Trebuchet MS', sans-serif;
}}

.stApp {{
    background: {BG};
}}

/* ---------- headings ---------- */
h1, h2, h3 {{
    color: {TEXT};
    font-weight: 700;
}}
h1 {{
    background: linear-gradient(90deg, {PRIMARY} 0%, {PRIMARY_LIGHT} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

/* ---------- masthead ---------- */
.mtl-hero {{
    background: linear-gradient(120deg, {PRIMARY} 0%, {PRIMARY_DARK} 100%);
    border-radius: 18px;
    padding: 1.4rem 1.8rem;
    color: #FFFFFF;
    margin-bottom: 1.2rem;
    box-shadow: 0 8px 24px rgba(230, 0, 126, 0.25);
}}
.mtl-hero h1 {{
    -webkit-text-fill-color: #FFFFFF !important;
    background: none !important;
    color: #FFFFFF !important;
    margin-bottom: 0.2rem;
}}
.mtl-hero p {{
    color: #FCE0EF;
    margin: 0;
    font-size: 0.95rem;
}}

/* ---------- cards ---------- */
.mtl-card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 1rem 1.2rem;
    box-shadow: 0 2px 10px rgba(230, 0, 126, 0.06);
    margin-bottom: 0.9rem;
}}
.mtl-card-hi {{
    background: {CARD_HI};
    border: 1px solid {PRIMARY_LIGHT};
}}
.mtl-badge {{
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #FFFFFF;
    background: {PRIMARY};
}}
.mtl-badge-gold {{
    background: {ACCENT_GOLD};
}}
.mtl-badge-good {{
    background: {GOOD};
}}
.mtl-badge-warn {{
    background: {WARN};
}}
.mtl-badge-bad {{
    background: {BAD};
}}
.mtl-note {{
    color: {TEXT_DIM};
    font-size: 0.85rem;
}}

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    border-bottom: 2px solid {BORDER};
}}
.stTabs [data-baseweb="tab"] {{
    height: 46px;
    border-radius: 10px 10px 0 0;
    background: transparent;
    padding: 0 1rem;
}}
.stTabs [data-baseweb="tab"] p {{
    color: {TEXT_DIM};
    font-weight: 600;
}}
.stTabs [aria-selected="true"] {{
    background: {CARD_HI};
}}
.stTabs [aria-selected="true"] p {{
    color: {PRIMARY} !important;
}}

/* ---------- buttons ---------- */
.stButton > button {{
    border-radius: 10px;
    border: 1px solid {PRIMARY};
    color: {PRIMARY};
    background: #FFFFFF;
    font-weight: 600;
}}
.stButton > button:hover {{
    background: {PRIMARY};
    color: #FFFFFF;
    border-color: {PRIMARY};
}}
.stButton > button[kind="primary"] {{
    background: {PRIMARY};
    color: #FFFFFF;
}}

/* ---------- metrics ---------- */
[data-testid="stMetric"] {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 0.7rem 0.9rem;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_DIM};
}}
[data-testid="stMetricValue"] {{
    color: {TEXT};
}}

/* ---------- dataframe ---------- */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
}}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{
    background: #FFFDFE;
    border-right: 1px solid {BORDER};
}}
"""


def plotly_layout(fig, height=380):
    fig.update_layout(
        font=dict(family=PLOTLY_FONT, color=TEXT, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig
