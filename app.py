import json
from pathlib import Path
import streamlit as st

# Page Config
st.set_page_config(
    page_title="Causeway — AI Portfolio Advisor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

OUTPUTS_DIR = Path(__file__).parent / "outputs"

# Static Data
PORTFOLIOS = {
    "PORTFOLIO_001": {
        "name": "Diversified",
        "sub": "38% Stocks, 62% Mutual Funds",
        "badge": "ACTIVE",
        "badge_bg": "#f59e0b",
        "badge_fg": "#0d0d0d",
    },
    "PORTFOLIO_002": {
        "name": "Concentrated Banking",
        "sub": "High concentration risk (91% Banking)",
        "badge": "HIGH RISK",
        "badge_bg": "#ef4444",
        "badge_fg": "#ffffff",
    },
    "PORTFOLIO_003": {
        "name": "Conservative",
        "sub": "21% Stocks, 79% Mutual Funds",
        "badge": "STABLE",
        "badge_bg": "#22c55e",
        "badge_fg": "#0d0d0d",
    },
}

# Helpers
def load_briefing(pid: str):
    files = sorted(OUTPUTS_DIR.glob(f"{pid}_*.json"), reverse=True)
    return json.loads(files[0].read_text()) if files else None

def grade(score: float) -> str:
    p = score * 100
    if p >= 90: return "A+"
    if p >= 85: return "A"
    if p >= 80: return "A−"
    if p >= 75: return "B+"
    return "B"

def signed(v: float) -> str:
    return f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"

# Session State
if "sel" not in st.session_state:
    st.session_state.sel = None

# Global CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: #0d0d0d !important;
    color: #d4d4d4;
    font-family: 'Inter', -apple-system, sans-serif;
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton { visibility: hidden !important; display: none !important; }

section[data-testid="stSidebar"] { display: none !important; }

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #0d0d0d !important;
}

.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

[data-testid="column"] { padding: 0 1rem !important; }

.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    background: transparent !important;
    color: #f59e0b !important;
    border: 1px solid rgba(245, 158, 11, 0.5) !important;
    border-radius: 2px !important;
    padding: 0.6rem 1.2rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: rgba(245, 158, 11, 0.1) !important;
    border-color: #f59e0b !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #1e1e1e !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #444 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 0.9rem 1.5rem !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #777 !important; }
.stTabs [aria-selected="true"] {
    color: #f59e0b !important;
    border-bottom: 2px solid #f59e0b !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #0f0f0f !important;
    padding: 2rem 2.5rem !important;
    border: 1px solid #1a1a1a !important;
    border-top: none !important;
}

hr { border-color: #1a1a1a !important; }
</style>
""", unsafe_allow_html=True)

# Nav Bar
st.markdown("""
<nav style="
    background: #0d0d0d;
    border-bottom: 1px solid #1a1a1a;
    padding: 0 max(3rem, 5vw);
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: space-between;
">
    <div>
        <span style="font-size:1.05rem;font-weight:900;color:#f59e0b;letter-spacing:0.18em;text-transform:uppercase;">CAUSEWAY</span>
        <div style="font-size:0.5rem;color:#2e2e2e;letter-spacing:0.28em;text-transform:uppercase;margin-top:1px;">Causal Reasoning for Portfolio Attribution</div>
    </div>
    <div>
        <span style="font-size:0.65rem;font-weight:600;color:#f59e0b;letter-spacing:0.15em;text-transform:uppercase;border-bottom:1.5px solid #f59e0b;padding-bottom:2px;">Intelligence</span>
    </div>
</nav>
""", unsafe_allow_html=True)

# Hero
st.markdown("""
<div style="padding: 5rem max(4rem, 5vw) 3.5rem; max-width: 1400px; margin: 0 auto;">
    <h1 style="
        font-family:'Inter',sans-serif;
        font-size: clamp(2.2rem, 4vw, 3.6rem);
        font-weight: 800;
        color: #e8e8e8;
        line-height: 1.08;
        letter-spacing: -0.025em;
        margin-bottom: 1.4rem;
    ">
        Uncover the <em style="color:#f59e0b;font-style:italic;">Causal Chains</em><br/>
        behind your performance.
    </h1>
    <p style="font-size:1rem;color:#555;line-height:1.75;max-width:500px;">
        Go beyond simple correlation. Our AI engine uses causal reasoning to
        attribute every basis point of movement to underlying macroeconomic
        drivers and sector shifts.
    </p>
</div>
""", unsafe_allow_html=True)

# Section Header
st.markdown("""
<div style="padding: 0 max(4rem, 5vw) 2rem; max-width: 1400px; margin: 0 auto;">
    <span style="font-size:0.6rem;font-weight:600;letter-spacing:0.3em;text-transform:uppercase;color:#444;">
        SELECT PORTFOLIO TO EVALUATE
    </span>
</div>
""", unsafe_allow_html=True)

# Portfolio Cards
st.markdown('<div style="padding: 0 max(4rem, 5vw); max-width: 1400px; margin: 0 auto;">', unsafe_allow_html=True)

card_cols = st.columns(3)
for i, (pid, info) in enumerate(PORTFOLIOS.items()):
    with card_cols[i]:
        is_sel = st.session_state.sel == pid
        border = "#f59e0b" if is_sel else "#1c1c1c"
        
        st.markdown(f"""
        <div style="
            background: #111;
            border: 1px solid {border};
            border-radius: 4px;
            padding: 1.75rem;
            margin-bottom: 1rem;
            transition: border-color 0.2s;
        ">
            <div style="display:flex;justify-content:flex-end;margin-bottom:1rem;">
                <span style="
                    font-size:0.58rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
                    background:{info['badge_bg']};color:{info['badge_fg']};
                    padding:0.25rem 0.65rem;border-radius:2px;
                ">{info['badge']}</span>
            </div>
            <h3 style="font-size:1rem;font-weight:700;color:#e8e8e8;margin-bottom:0.5rem;letter-spacing:-0.01em;">
                {pid}
            </h3>
            <p style="font-size:0.85rem;color:#666;margin-bottom:0.4rem;">{info['name']}</p>
            <p style="font-size:0.78rem;color:#444;margin:0;">{info['sub']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        label = "SELECTED" if is_sel else "ANALYZE"
        if st.button(label, key=f"btn_{pid}"):
            st.session_state.sel = pid
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# Results Section
st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)

if st.session_state.sel:
    pid = st.session_state.sel
    briefing = load_briefing(pid)

    if briefing is None:
        st.error(f"No output found for {pid}. Run: python run.py --portfolio {pid}")
    else:
        conf = briefing["confidence_score"]
        breakdown = briefing.get("confidence_breakdown", {})

        # Confidence Metrics
        col1, col2, _ = st.columns([1, 1, 2])
        with col1:
            st.markdown(f"""
            <div style="padding:1.5rem;background:#0f0f0f;border:1px solid #1a1a1a;border-radius:4px;">
                <div style="font-size:0.58rem;font-weight:600;letter-spacing:0.25em;color:#444;text-transform:uppercase;margin-bottom:0.5rem;">Confidence Score</div>
                <div style="font-size:3rem;font-weight:900;color:#f59e0b;line-height:1;">
                    {conf*100:.1f}<span style="font-size:1.2rem;">%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="padding:1.5rem;background:#0f0f0f;border:1px solid #1a1a1a;border-radius:4px;">
                <div style="font-size:0.58rem;font-weight:600;letter-spacing:0.25em;color:#444;text-transform:uppercase;margin-bottom:0.5rem;">Evaluation Score</div>
                <div style="font-size:3rem;font-weight:900;color:#e8e8e8;line-height:1;">{grade(conf)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Confidence Breakdown
        st.markdown('<div style="margin-top:1.5rem;"></div>', unsafe_allow_html=True)
        st.markdown("#### CONFIDENCE BREAKDOWN")
        
        # Breakdown bars
        bars_html = ""
        for key, val in breakdown.items():
            label = key.replace("_", " ").title()
            color = "#f59e0b" if val >= 0.8 else "#888"
            bars_html += f"""
                <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.6rem;">
                    <div style="font-size:0.7rem;color:#666;width:180px;">{label}</div>
                    <div style="flex:1;height:3px;background:#1a1a1a;border-radius:2px;overflow:hidden;">
                        <div style="width:{val*100:.0f}%;height:100%;background:{color};"></div>
                    </div>
                    <div style="font-size:0.7rem;font-weight:600;color:{color};width:40px;text-align:right;">{val*100:.0f}%</div>
                </div>
            """
        st.markdown(bars_html, unsafe_allow_html=True)
        
        st.markdown("</div></div></div>", unsafe_allow_html=True)
        
        # Tabs
        st.markdown('<div style="padding: 0 max(4rem, 5vw); max-width: 1400px; margin: 0 auto;">', unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["KEY DRIVERS", "CAUSAL CHAIN", "CONFLICTING SIGNALS", "RECOMMENDATIONS"])
        
        # Tab 1: Key Drivers
        with tab1:
            st.markdown('<h3 style="font-size:0.8rem;font-weight:700;color:#e8e8e8;margin-bottom:1.5rem;letter-spacing:0.1em;text-transform:uppercase;">Dominant Drivers</h3>', unsafe_allow_html=True)

            drivers_html = ""
            for i, kd in enumerate(briefing.get("key_drivers", []), 1):
                drivers_html += f"""
                <div style="padding:1rem 0;border-bottom:1px solid #181818;">
                    <div style="font-size:0.7rem;color:#f59e0b;font-weight:600;margin-bottom:0.4rem;">DRIVER {i}</div>
                    <p style="font-size:0.85rem;color:#aaa;line-height:1.6;margin:0;">{kd}</p>
                </div>
                """
            st.markdown(drivers_html, unsafe_allow_html=True)
        
        # Tab 2: Causal Chain
        with tab2:
            chain = briefing.get("causal_chain", [])
            LEVEL_COLORS = {
                "NEWS": "blue",
                "SECTOR": "orange",
                "STOCK": "green",
                "PORTFOLIO": "red",
            }

            for lvl, color in LEVEL_COLORS.items():
                items = [it for it in chain if it.get("level") == lvl]
                if not items:
                    continue

                st.markdown(f"### :{color}[{lvl}]")
                
                for it in items:
                    mag = it.get("magnitude")
                    if mag is not None:
                        mag_color = "green" if mag > 0 else "red"
                        st.markdown(f"**{it.get('entity', '')}** :{mag_color}[{signed(mag)}]")
                    else:
                        st.markdown(f"**{it.get('entity', '')}**")
                    st.write(it.get('impact', ''))
                    st.divider()

        
        # Tab 3: Conflicting Signals
        with tab3:
            conflicts = briefing.get("conflicting_signals", [])
            if not conflicts:
                st.markdown('<div style="text-align:center;padding:3rem 2rem;color:#444;font-size:0.8rem;">No conflicting signals detected</div>', unsafe_allow_html=True)
            else:
                conflicts_html = ""
                for c in conflicts:
                    entity = c.get('entity', '—').replace('<', '&lt;').replace('>', '&gt;')
                    ns = c.get("news_sentiment", "—")
                    pm = c.get("price_movement", "—")
                    explanation = c.get('explanation', '').replace('<', '&lt;').replace('>', '&gt;')

                    conflicts_html += f"""
                    <div style="background:#0d0d0d;border:1px solid #1a1a1a;padding:1.5rem;margin-bottom:1rem;">
                        <div style="font-size:0.9rem;font-weight:700;color:#e8e8e8;margin-bottom:1rem;">{entity}</div>
                        <div style="display:flex;gap:3rem;margin-bottom:1rem;">
                            <div>
                                <div style="font-size:0.6rem;color:#444;text-transform:uppercase;margin-bottom:0.3rem;">News Sentiment</div>
                                <div style="font-size:0.85rem;font-weight:600;color:#f59e0b;">{ns}</div>
                            </div>
                            <div>
                                <div style="font-size:0.6rem;color:#444;text-transform:uppercase;margin-bottom:0.3rem;">Price Movement</div>
                                <div style="font-size:0.85rem;font-weight:600;color:#ef4444;">{pm}</div>
                            </div>
                        </div>
                        <div style="font-size:0.82rem;color:#777;line-height:1.65;border-top:1px solid #181818;padding-top:1rem;">{explanation}</div>
                    </div>
                    """
                st.markdown(conflicts_html, unsafe_allow_html=True)
        
        # Tab 4: Recommendations
        with tab4:
            recs = briefing.get("recommendations", [])
            recs_html = ""
            for i, rec in enumerate(recs, 1):
                rec_safe = rec.replace('<', '&lt;').replace('>', '&gt;')
                recs_html += f"""
                <div style="display:flex;gap:1rem;padding:1.25rem;background:#0d0d0d;border:1px solid #1a1a1a;margin-bottom:0.8rem;">
                    <div style="min-width:32px;height:32px;background:#f59e0b;color:#0d0d0d;font-size:0.7rem;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0;">{i}</div>
                    <p style="font-size:0.88rem;color:#bbb;line-height:1.65;margin:0;">{rec_safe}</p>
                </div>
                """
            st.markdown(recs_html, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("""
<footer style="
    margin-top: 5rem;
    padding: 2rem max(4rem, 5vw);
    border-top: 1px solid #161616;
    text-align: center;
">
    <span style="font-size:0.7rem;font-weight:900;color:#f59e0b;letter-spacing:0.2em;">CAUSEWAY</span>
    <div style="font-size:0.65rem;color:#333;margin-top:0.5rem;">Built with Gemini 2.5 Flash</div>
</footer>
""", unsafe_allow_html=True)