import html
import json
import math
import re
import socket
import ssl
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

import streamlit as st


APP_TITLE = "CHESSTALKER Pro"
APP_ICON = "C"
APP_SCHEMA_VERSION = 4
DEFAULT_MONTHS = 8
DEFAULT_MAX_GAMES = 120
DEFAULT_MULTI_PV = 3
DEFAULT_RANGE_DAYS = 120
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
REQUEST_TIMEOUT = 20
USER_AGENT = "chesstalker-pro/1.0 (public profile analyzer)"
DRAW_RESULTS = {
    "agreed",
    "repetition",
    "stalemate",
    "insufficient",
    "50move",
    "timevsinsufficient",
    "draw",
}
LOSS_RESULTS = {
    "abandoned",
    "checkmated",
    "lose",
    "resigned",
    "timeout",
}
RATING_LABELS = {
    "chess_bullet": "Bullet",
    "chess_blitz": "Blitz",
    "chess_rapid": "Rapid",
    "chess_daily": "Daily",
    "chess960_daily": "960 Daily",
    "chess960": "Chess960",
}
TIME_CLASS_LABELS = {
    "bullet": "Bullet",
    "blitz": "Blitz",
    "rapid": "Rapid",
    "daily": "Daily",
    "unknown": "Other",
}
TIME_CLASS_FILTER_OPTIONS = ["blitz", "rapid", "bullet", "daily", "unknown"]
DEFAULT_TIME_CLASS_FILTERS = ["blitz", "rapid", "bullet", "daily"]
DATE_PRESET_OPTIONS = ["Last 30 days", "Last 90 days", "Last 180 days", "This year", "Custom"]
PIECE_MAP = {
    "K": "&#9812;",
    "Q": "&#9813;",
    "R": "&#9814;",
    "B": "&#9815;",
    "N": "&#9816;",
    "P": "&#9817;",
    "k": "&#9818;",
    "q": "&#9819;",
    "r": "&#9820;",
    "b": "&#9821;",
    "n": "&#9822;",
    "p": "&#9823;",
}
OPENING_STOP_WORDS = {
    "accepted",
    "attack",
    "classical",
    "declined",
    "defense",
    "defence",
    "game",
    "gambit",
    "opening",
    "system",
    "variation",
}


st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        :root {
            --bg-1: #08121d;
            --bg-2: #11293d;
            --card: rgba(10, 23, 37, 0.82);
            --card-soft: rgba(21, 42, 64, 0.78);
            --ink: #17263a;
            --muted: #6d7f95;
            --accent: #ffb347;
            --accent-2: #69d2e7;
            --success: #6ee7b7;
            --danger: #fda4af;
            --line: rgba(161, 197, 226, 0.18);
        }

        .stApp {
            background:
                linear-gradient(rgba(214, 224, 236, 0.45) 1px, transparent 1px),
                linear-gradient(90deg, rgba(214, 224, 236, 0.45) 1px, transparent 1px),
                radial-gradient(circle at 15% 20%, rgba(255, 179, 71, 0.08), transparent 28%),
                radial-gradient(circle at 90% 10%, rgba(105, 210, 231, 0.08), transparent 26%),
                linear-gradient(180deg, #f7fafc 0%, #edf3f8 100%);
            background-size: 34px 34px, 34px 34px, auto, auto, auto;
            color: var(--ink);
            font-family: 'Space Grotesk', sans-serif;
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
        }

        h1, h2, h3, h4, h5, h6, p, label, li, span, div {
            font-family: 'Space Grotesk', sans-serif;
        }

        code, pre, .stCodeBlock {
            font-family: 'IBM Plex Mono', monospace !important;
        }

        .hero-panel {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 28px;
            padding: 28px 30px;
            margin-bottom: 18px;
            background:
                linear-gradient(140deg, rgba(10, 23, 37, 0.94) 0%, rgba(14, 35, 53, 0.86) 55%, rgba(18, 58, 86, 0.82) 100%);
            box-shadow: 0 18px 60px rgba(0, 0, 0, 0.32);
        }

        .hero-panel::after {
            content: "";
            position: absolute;
            inset: auto -10% -40% auto;
            width: 340px;
            height: 340px;
            background: radial-gradient(circle, rgba(255, 179, 71, 0.24) 0%, transparent 66%);
            pointer-events: none;
        }

        .eyebrow {
            color: var(--accent);
            font-size: 0.88rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }

        .hero-title {
            font-size: 2.55rem;
            line-height: 1.02;
            font-weight: 700;
            margin: 0 0 0.55rem;
        }

        .hero-copy {
            max-width: 760px;
            color: #d3e4f1;
            font-size: 1rem;
            line-height: 1.6;
            margin-bottom: 0.25rem;
        }

        .glass-card {
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 18px 18px 14px;
            background: var(--card);
            box-shadow: 0 12px 34px rgba(2, 8, 16, 0.25);
            margin-bottom: 14px;
        }

        .section-card {
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 18px;
            background: var(--card-soft);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
            margin-bottom: 14px;
        }

        .section-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin: 0 0 0.5rem;
            color: #f6fbff;
        }

        .section-copy {
            color: var(--muted);
            line-height: 1.55;
        }

        .insight-banner {
            border: 1px solid rgba(255, 179, 71, 0.18);
            border-radius: 24px;
            padding: 20px 22px;
            margin-bottom: 14px;
            background: linear-gradient(135deg, rgba(255, 179, 71, 0.12) 0%, rgba(105, 210, 231, 0.10) 100%);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.16);
        }

        .insight-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: #fff7ea;
            margin-bottom: 0.4rem;
        }

        .insight-copy {
            color: #e4eff8;
            line-height: 1.6;
        }

        .list-card {
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 18px;
            background: rgba(10, 23, 37, 0.84);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
            margin-bottom: 14px;
        }

        .list-card.good {
            border-color: rgba(110, 231, 183, 0.18);
        }

        .list-card.warn {
            border-color: rgba(253, 164, 175, 0.18);
        }

        .list-card.neutral {
            border-color: rgba(105, 210, 231, 0.18);
        }

        .list-card ul, .list-card ol {
            margin: 0.35rem 0 0 1.15rem;
            padding: 0;
            color: #d9e8f3;
        }

        .list-card li {
            margin-bottom: 0.5rem;
            line-height: 1.55;
            color: #d9e8f3;
        }

        .fact-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }

        .fact-item {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 18px;
            padding: 14px;
            background: rgba(255, 255, 255, 0.03);
        }

        .fact-label {
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.4rem;
        }

        .fact-value {
            color: #ffffff;
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .summary-deck {
            display: grid;
            grid-template-columns: 1.08fr 1fr;
            gap: 18px;
            margin-bottom: 20px;
        }

        .summary-card {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(207, 219, 231, 0.9);
            border-radius: 28px;
            padding: 24px 26px;
            box-shadow: 0 18px 44px rgba(32, 54, 79, 0.10);
            color: #162235;
        }

        .summary-head {
            display: flex;
            align-items: flex-start;
            gap: 18px;
            justify-content: space-between;
        }

        .avatar-box {
            width: 84px;
            height: 84px;
            border-radius: 20px;
            background: #162235;
            color: #19c48f;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.4rem;
            font-weight: 700;
            box-shadow: inset 0 0 0 3px rgba(25, 196, 143, 0.14);
        }

        .identity-box {
            flex: 1;
            min-width: 0;
        }

        .identity-name {
            font-size: 2rem;
            font-weight: 700;
            color: #1a2538;
            line-height: 1.1;
            margin-bottom: 0.7rem;
        }

        .identity-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.4rem 0.9rem;
            border-radius: 999px;
            background: rgba(31, 197, 131, 0.12);
            color: #0d9b68;
            font-weight: 700;
            margin-bottom: 0.75rem;
        }

        .identity-range {
            display: inline-flex;
            flex-wrap: wrap;
            gap: 6px;
            padding: 0.5rem 0.9rem;
            border-radius: 999px;
            background: #eef3f8;
            color: #64758f;
            font-weight: 600;
        }

        .ovr-box {
            min-width: 146px;
            display: flex;
            justify-content: flex-end;
        }

        .ring {
            --progress: 50;
            width: 106px;
            height: 106px;
            border-radius: 50%;
            background: conic-gradient(#e18b1e calc(var(--progress) * 1%), #e7eef5 0);
            display: grid;
            place-items: center;
        }

        .ring-teal {
            background: conic-gradient(#28a38c calc(var(--progress) * 1%), #e7eef5 0);
        }

        .ring-inner {
            width: 82px;
            height: 82px;
            border-radius: 50%;
            background: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: #17263a;
        }

        .ring-inner span {
            color: #8b9ab0;
            font-size: 0.95rem;
            font-weight: 700;
        }

        .ring-inner strong {
            font-size: 2rem;
            line-height: 1;
            color: #18263a;
        }

        .mini-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-top: 22px;
            margin-bottom: 18px;
        }

        .mini-stat {
            text-align: center;
        }

        .mini-value {
            font-size: 2rem;
            font-weight: 700;
            color: #d88015;
            line-height: 1;
            margin-bottom: 0.45rem;
        }

        .mini-label {
            font-size: 0.92rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #92a0b3;
            margin-bottom: 0.65rem;
        }

        .mini-bar {
            height: 6px;
            border-radius: 999px;
            background: #e9eef4;
            overflow: hidden;
        }

        .mini-bar span {
            display: block;
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #e89a28 0%, #ea5a2e 100%);
        }

        .rating-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
        }

        .rating-pill {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            padding: 16px 18px;
            border-radius: 20px;
            background: #f5f8fb;
            color: #8aa0bd;
            font-size: 0.98rem;
            font-weight: 600;
        }

        .rating-pill strong {
            color: #263549;
            font-size: 1.15rem;
        }

        .summary-footer {
            margin-top: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }

        .summary-tag {
            padding: 0.55rem 0.95rem;
            border-radius: 999px;
            border: 1px solid rgba(232, 154, 40, 0.28);
            background: rgba(232, 154, 40, 0.10);
            color: #d9861f;
            font-weight: 700;
        }

        .summary-record {
            display: flex;
            align-items: center;
            gap: 14px;
            font-size: 1rem;
            font-weight: 700;
            color: #8a99ac;
        }

        .summary-record .win {
            color: #149e78;
        }

        .summary-record .loss {
            color: #d94a43;
        }

        .summary-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 18px;
        }

        .summary-title {
            color: #1b273a;
            font-size: 1.9rem;
            font-weight: 700;
        }

        .summary-predict {
            padding: 0.55rem 0.95rem;
            border-radius: 999px;
            background: rgba(31, 197, 131, 0.10);
            border: 1px solid rgba(31, 197, 131, 0.18);
            color: #0f8f64;
            font-weight: 700;
        }

        .stalker-layout {
            display: grid;
            grid-template-columns: 196px 1fr;
            align-items: center;
            gap: 22px;
        }

        .stalker-ring {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .stalker-risks {
            display: grid;
            gap: 18px;
        }

        .risk-row {
            display: grid;
            gap: 8px;
        }

        .risk-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            color: #243247;
            font-size: 0.98rem;
        }

        .risk-top strong {
            font-size: 1rem;
            color: #19263a;
        }

        .risk-bar {
            height: 10px;
            border-radius: 999px;
            background: #e8edf4;
            overflow: hidden;
        }

        .risk-bar span {
            display: block;
            height: 100%;
            border-radius: 999px;
        }

        @media (max-width: 1100px) {
            .summary-deck {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 780px) {
            .summary-head,
            .stalker-layout {
                grid-template-columns: 1fr;
                display: grid;
            }
            .mini-grid,
            .rating-grid,
            .fact-grid {
                grid-template-columns: 1fr 1fr;
            }
            .ovr-box {
                justify-content: flex-start;
            }
        }

        .chip-row {
            margin-top: 0.8rem;
        }

        .chip {
            display: inline-block;
            margin: 0 0.45rem 0.45rem 0;
            padding: 0.46rem 0.75rem;
            border-radius: 999px;
            font-size: 0.84rem;
            background: rgba(255, 255, 255, 0.08);
            color: #eff8ff;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .chip.good {
            background: rgba(110, 231, 183, 0.14);
            color: #c8fff0;
            border-color: rgba(110, 231, 183, 0.18);
        }

        .chip.warn {
            background: rgba(253, 164, 175, 0.13);
            color: #ffe4e8;
            border-color: rgba(253, 164, 175, 0.16);
        }

        .metric-card {
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 16px;
            min-height: 132px;
            background: linear-gradient(180deg, rgba(12, 24, 38, 0.92) 0%, rgba(17, 39, 58, 0.88) 100%);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.2);
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.84rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.6rem;
        }

        .metric-value {
            font-size: 2rem;
            line-height: 1;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.4rem;
        }

        .metric-note {
            color: #cfe3f4;
            font-size: 0.94rem;
            line-height: 1.45;
        }

        .board-shell {
            display: inline-block;
            padding: 16px;
            border-radius: 22px;
            border: 1px solid var(--line);
            background: rgba(10, 23, 37, 0.9);
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.24);
        }

        .board-grid {
            display: grid;
            grid-template-columns: repeat(8, 62px);
            grid-template-rows: repeat(8, 62px);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .square {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.3rem;
        }

        .sq-light {
            background: #f1d9b5;
            color: #181818;
        }

        .sq-dark {
            background: #b58863;
            color: #181818;
        }

        .sq-highlight {
            box-shadow: inset 0 0 0 4px rgba(105, 210, 231, 0.9);
        }

        .coord {
            position: absolute;
            left: 6px;
            bottom: 5px;
            font-size: 0.65rem;
            font-weight: 700;
            opacity: 0.72;
        }

        div[data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 12px;
            background: rgba(10, 23, 37, 0.82);
        }

        div[data-testid="stMetric"] label {
            color: var(--muted) !important;
        }

        div[data-testid="stMetricValue"] {
            color: white !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }

        .stTabs [data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            color: #dceaf6;
            padding: 10px 16px;
        }

        .stTabs [aria-selected="true"] {
            background: rgba(255, 179, 71, 0.15) !important;
            color: white !important;
        }

        .stDataFrame, .stTable {
            border: 1px solid var(--line);
            border-radius: 18px;
            overflow: hidden;
        }

        .small-note {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_mean(values):
    return mean(values) if values else None


def fmt_int(value):
    if value is None:
        return "N/A"
    return f"{int(round(value)):,}"


def fmt_percent(value):
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def fmt_score(score):
    if score is None:
        return "N/A"
    return f"{score:.2f}/1.00"


def pretty_label(label):
    return TIME_CLASS_LABELS.get(label.lower(), label)


def fmt_delta(value):
    if value is None:
        return "N/A"
    rounded = int(round(value))
    return f"+{rounded}" if rounded > 0 else str(rounded)


def selected_class_caption(selected_classes):
    if not selected_classes:
        return "All time controls"
    return ", ".join(pretty_label(item) for item in selected_classes)


def score_band(score):
    if score is None:
        return "Unknown"
    if score >= 0.68:
        return "Crushing"
    if score >= 0.58:
        return "Strong"
    if score >= 0.48:
        return "Balanced"
    if score >= 0.38:
        return "Shaky"
    return "Danger"


def confidence_label(total_games, rated_share):
    if total_games >= 80 and (rated_share or 0) >= 80:
        return "High confidence"
    if total_games >= 35:
        return "Good confidence"
    if total_games >= 15:
        return "Medium confidence"
    return "Low confidence"


def analysis_is_compatible(summary):
    if not isinstance(summary, dict):
        return False
    required_keys = {
        "profile_name",
        "selected_time_classes",
        "avg_player",
        "style_tags",
        "focus_plan",
        "coach_blueprint",
        "time_ranked",
        "phase_ranked",
        "rating_rows",
        "recent_games",
    }
    return required_keys.issubset(summary.keys())


def ensure_runtime_state():
    current_version = st.session_state.get("app_schema_version")
    if current_version != APP_SCHEMA_VERSION:
        st.session_state["analysis"] = None
        st.session_state["opponent_summary"] = None
        st.session_state["app_schema_version"] = APP_SCHEMA_VERSION
    if "selected_time_classes" not in st.session_state:
        st.session_state["selected_time_classes"] = DEFAULT_TIME_CLASS_FILTERS.copy()
    if "range_preset" not in st.session_state:
        st.session_state["range_preset"] = "Last 90 days"
    if "start_date" not in st.session_state:
        st.session_state["start_date"] = date.today() - timedelta(days=DEFAULT_RANGE_DAYS)
    if "end_date" not in st.session_state:
        st.session_state["end_date"] = date.today()


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def resolve_date_preset(preset_name):
    today = date.today()
    if preset_name == "Last 30 days":
        return today - timedelta(days=30), today
    if preset_name == "Last 90 days":
        return today - timedelta(days=90), today
    if preset_name == "Last 180 days":
        return today - timedelta(days=180), today
    if preset_name == "This year":
        return date(today.year, 1, 1), today
    return None


def format_short_date(value):
    return value.strftime("%b %d")


def format_date_range(start_date, end_date):
    if start_date.year == end_date.year:
        return f"{start_date.strftime('%b %d')} -> {end_date.strftime('%b %d')}"
    return f"{start_date.strftime('%b %d, %Y')} -> {end_date.strftime('%b %d, %Y')}"


def month_overlaps_range(year_value, month_value, start_date, end_date):
    month_start = date(year_value, month_value, 1)
    if month_value == 12:
        month_end = date(year_value + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year_value, month_value + 1, 1) - timedelta(days=1)
    return month_end >= start_date and month_start <= end_date


def format_epoch(epoch_value):
    if not epoch_value:
        return "Unknown"
    return datetime.fromtimestamp(int(epoch_value), tz=timezone.utc).strftime("%Y-%m-%d")


def normalize_username(username):
    return username.strip().lower().replace(" ", "")


def service_name_from_url(url):
    host = urlparse(url).netloc.lower()
    if "chess.com" in host:
        return "Chess.com"
    if "lichess.org" in host:
        return "Lichess"
    return host or "the API"


def diagnose_network_error(exc):
    reason = getattr(exc, "reason", exc)
    reason_text = str(reason)
    lower_reason = reason_text.lower()
    if isinstance(reason, socket.gaierror) or "getaddrinfo" in lower_reason or "name resolution" in lower_reason:
        return (
            "DNS lookup failed",
            "Your computer could not translate the API address. Check Wi-Fi/DNS, VPN, or firewall settings.",
        )
    if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in lower_reason:
        return (
            "Connection timed out",
            "The server did not answer fast enough. Try again, or use a smaller date range for fewer archive requests.",
        )
    if isinstance(reason, ssl.SSLError) or "certificate" in lower_reason or "ssl" in lower_reason:
        return (
            "Secure connection failed",
            "A proxy, antivirus, or system certificate setting may be blocking the HTTPS request.",
        )
    if "forcibly closed" in lower_reason or "connection reset" in lower_reason:
        return (
            "Connection was reset",
            "The remote service or your network closed the request. Try again in a minute.",
        )
    if "network is unreachable" in lower_reason or "no route" in lower_reason:
        return (
            "Network is unreachable",
            "Your computer currently has no working route to the internet.",
        )
    return ("Connection failed", reason_text or "No extra detail was provided by Windows.")


def build_network_error_message(url, exc, attempts):
    service_name = service_name_from_url(url)
    problem, advice = diagnose_network_error(exc)
    host = urlparse(url).netloc or "unknown host"
    return (
        f"{service_name} connection problem: {problem}.\n\n"
        f"I tried to reach {host} {attempts} times, but Windows reported: {advice}\n\n"
        "Quick checks:\n"
        "1. Open the Chess.com profile in your browser to confirm the internet works.\n"
        "2. Try again with a smaller date range, like Last 30 days.\n"
        "3. Turn off VPN/proxy temporarily if it blocks Python apps.\n"
        "4. If the browser works but the app does not, restart Streamlit and run it again.\n"
        "5. If DNS keeps failing, switch Data source to Paste PGN and analyze exported games offline."
    )


def build_http_error_message(url, exc, detail):
    service_name = service_name_from_url(url)
    if exc.code == 404:
        return (
            f"{service_name} could not find that profile or archive.\n\n"
            "Check the username spelling exactly as it appears on Chess.com."
        )
    if exc.code == 403:
        return (
            f"{service_name} blocked this request with status 403.\n\n"
            "Try again later, or open the profile in your browser first. Some networks block public API requests from Python."
        )
    if exc.code == 429:
        return (
            f"{service_name} is rate limiting requests right now.\n\n"
            "Wait 1-2 minutes, then try again with a smaller date range."
        )
    if exc.code in {500, 502, 503, 504}:
        return (
            f"{service_name} is having a temporary server problem ({exc.code}).\n\n"
            "Try again in a minute. Your settings are still saved."
        )
    return f"{service_name} request failed with status {exc.code}: {detail[:220]}"


def request_json(url, attempts=3):
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in {500, 502, 503, 504} and attempt < attempts:
                time.sleep(0.6 * attempt)
                continue
            raise RuntimeError(build_http_error_message(url, exc, detail)) from exc
        except (URLError, TimeoutError, socket.timeout, ssl.SSLError, OSError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(0.6 * attempt)
                continue
            raise RuntimeError(build_network_error_message(url, exc, attempts)) from exc
    raise RuntimeError(build_network_error_message(url, last_error, attempts))


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_json_cached(url):
    return request_json(url)


def parse_pgn_headers(pgn_text):
    headers = {}
    for line in pgn_text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        match = re.match(r'^\[(\w+)\s+"(.*)"\]$', line)
        if match:
            headers[match.group(1)] = match.group(2)
    return headers


def strip_pgn_variations(text):
    pattern = re.compile(r"\([^()]*\)")
    while True:
        updated = pattern.sub(" ", text)
        if updated == text:
            return updated
        text = updated


def extract_moves_from_pgn(pgn_text):
    move_lines = [line for line in pgn_text.splitlines() if not line.startswith("[")]
    move_text = " ".join(move_lines)
    move_text = re.sub(r"\{[^}]*\}", " ", move_text)
    move_text = re.sub(r";[^\n]*", " ", move_text)
    move_text = strip_pgn_variations(move_text)
    move_text = re.sub(r"\$\d+", " ", move_text)
    move_text = move_text.replace("\n", " ")
    move_text = re.sub(r"\s+", " ", move_text).strip()
    tokens = []
    for token in move_text.split(" "):
        if not token:
            continue
        token = re.sub(r"^\d+\.(\.\.)?", "", token)
        if not token:
            continue
        if re.match(r"^\d+\.(\.\.)?$", token):
            continue
        if re.match(r"^\d+\.+$", token):
            continue
        if token in {"1-0", "0-1", "1/2-1/2", "*"}:
            continue
        tokens.append(token)
    return tokens


def classify_phase(move_count):
    if move_count <= 20:
        return "Opening"
    if move_count <= 40:
        return "Middlegame"
    return "Endgame"


def classify_length(move_count):
    if move_count <= 20:
        return "Short"
    if move_count <= 45:
        return "Medium"
    return "Long"


def determine_outcome(player_result, opponent_result, result_tag, is_white):
    if player_result == "win" or opponent_result in LOSS_RESULTS:
        return "Win", 1.0
    if opponent_result == "win" or player_result in LOSS_RESULTS:
        return "Loss", 0.0
    if player_result in DRAW_RESULTS or opponent_result in DRAW_RESULTS:
        return "Draw", 0.5
    if result_tag == "1/2-1/2":
        return "Draw", 0.5
    if result_tag == "1-0":
        return ("Win", 1.0) if is_white else ("Loss", 0.0)
    if result_tag == "0-1":
        return ("Loss", 0.0) if is_white else ("Win", 1.0)
    return "Draw", 0.5


def opening_family(opening_name):
    if not opening_name:
        return "Unknown"
    family = re.split(r":|,|\(|-", opening_name)[0].strip()
    return family or opening_name


def opening_tokens(opening_name):
    if not opening_name or opening_name.lower() == "unknown":
        return set()
    tokens = re.findall(r"[a-zA-Z0-9']+", opening_name.lower())
    return {
        token
        for token in tokens
        if len(token) > 2 and token not in OPENING_STOP_WORDS
    }


def clean_opening_name(raw_name):
    if not raw_name:
        return "Unknown"
    cleaned = str(raw_name).strip()
    if cleaned.startswith("http"):
        cleaned = cleaned.rstrip("/").split("/")[-1].replace("-", " ").replace("%20", " ")
    return cleaned or "Unknown"


def format_result_reason(result_code):
    text = result_code.replace("_", " ").strip()
    return text.title() if text else "Unknown"


def uci_to_text(uci_move):
    if len(uci_move) < 4:
        return uci_move
    move_text = f"{uci_move[:2]}-{uci_move[2:4]}"
    if len(uci_move) == 5:
        move_text += f"={uci_move[4].upper()}"
    return move_text


def move_signature(tokens, color):
    if not tokens:
        return ""
    if color == "white":
        relevant = [tokens[index] for index in (0, 2, 4) if index < len(tokens)]
    else:
        relevant = [tokens[index] for index in (1, 3, 5) if index < len(tokens)]
    return " ".join(relevant).strip()


def performance_rating(avg_opponent_rating, score_fraction):
    if avg_opponent_rating is None or score_fraction is None:
        return None
    bounded = min(max(score_fraction, 0.01), 0.99)
    rating_delta = -400 * math.log10((1 / bounded) - 1)
    return avg_opponent_rating + rating_delta


def bucket_summary(label, games):
    total = len(games)
    if total == 0:
        return None
    wins = sum(1 for game in games if game["outcome"] == "Win")
    draws = sum(1 for game in games if game["outcome"] == "Draw")
    losses = total - wins - draws
    score_total = sum(game["score"] for game in games)
    avg_opp = safe_mean(
        [game["opponent_rating"] for game in games if game["opponent_rating"] is not None]
    )
    avg_user = safe_mean([game["player_rating"] for game in games if game["player_rating"] is not None])
    avg_accuracy = safe_mean([game["accuracy"] for game in games if game["accuracy"] is not None])
    avg_opp_accuracy = safe_mean(
        [game["opponent_accuracy"] for game in games if game["opponent_accuracy"] is not None]
    )
    phase_perf = performance_rating(avg_opp, score_total / total)
    return {
        "label": label,
        "games": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "score_pct": (score_total / total) * 100,
        "win_pct": (wins / total) * 100,
        "avg_opponent": avg_opp,
        "avg_player": avg_user,
        "performance": phase_perf,
        "avg_accuracy": avg_accuracy,
        "avg_opponent_accuracy": avg_opp_accuracy,
    }


def sort_bucket_rows(bucket_map, minimum_games=1, reverse=True):
    rows = [row for row in bucket_map.values() if row and row["games"] >= minimum_games]
    return sorted(
        rows,
        key=lambda row: (row["score_pct"], row["games"], row["win_pct"]),
        reverse=reverse,
    )


def top_rows_as_table(rows, limit=8):
    table = []
    for row in rows[:limit]:
        table.append(
            {
                "Category": pretty_label(row["label"]),
                "Games": row["games"],
                "Score %": round(row["score_pct"], 1),
                "Win %": round(row["win_pct"], 1),
                "Perf": int(round(row["performance"])) if row["performance"] is not None else None,
            }
        )
    return table


def extract_rating_snapshot(stats):
    rows = []
    for key, label in RATING_LABELS.items():
        node = stats.get(key)
        if not isinstance(node, dict):
            continue
        last_rating = ((node.get("last") or {}).get("rating"))
        best_rating = ((node.get("best") or {}).get("rating"))
        record = node.get("record") or {}
        wins = record.get("win")
        losses = record.get("loss")
        draws = record.get("draw")
        rows.append(
            {
                "format_key": key,
                "label": label,
                "last": last_rating,
                "best": best_rating,
                "games": (wins or 0) + (losses or 0) + (draws or 0),
            }
        )
    return rows


def detect_main_format(games, rating_rows):
    game_counts = Counter(game["time_class"] for game in games)
    if game_counts:
        primary_time_class, _ = game_counts.most_common(1)[0]
        expected_key = f"chess_{primary_time_class.lower()}"
        for row in rating_rows:
            if row["format_key"] == expected_key and row["last"] is not None:
                return row["label"], row["last"]
    usable = [row for row in rating_rows if row["last"] is not None]
    if usable:
        usable.sort(key=lambda row: (row["games"], row["last"]), reverse=True)
        return usable[0]["label"], usable[0]["last"]
    avg_rating = safe_mean([game["player_rating"] for game in games if game["player_rating"] is not None])
    return "Recent games", avg_rating


def summarize_rating_event(game):
    if game.get("opponent_rating") is None or game.get("player_rating") is None:
        return None
    return {
        "date": game["ended_at"].strftime("%Y-%m-%d"),
        "opponent": game["opponent_name"],
        "opening": game["opening_family"],
        "format": pretty_label(game["time_class"]),
        "player_rating": game["player_rating"],
        "opponent_rating": game["opponent_rating"],
        "gap": game["opponent_rating"] - game["player_rating"],
        "result": game["outcome"],
    }


def choose_extreme_game(games, key_func, reverse=True):
    candidates = [summarize_rating_event(game) for game in games]
    candidates = [candidate for candidate in candidates if candidate]
    if not candidates:
        return None
    candidates.sort(key=key_func, reverse=reverse)
    return candidates[0]


def bucket_to_detail_table(rows, limit=8):
    table = []
    for row in rows[:limit]:
        table.append(
            {
                "Category": pretty_label(row["label"]),
                "Games": row["games"],
                "Score %": round(row["score_pct"], 1),
                "Win %": round(row["win_pct"], 1),
                "Avg You": int(round(row["avg_player"])) if row["avg_player"] is not None else None,
                "Avg Opp": int(round(row["avg_opponent"])) if row["avg_opponent"] is not None else None,
                "Perf": int(round(row["performance"])) if row["performance"] is not None else None,
                "Accuracy": round(row["avg_accuracy"], 1) if row["avg_accuracy"] is not None else None,
            }
        )
    return table


def counter_to_table(counter_obj, label_name):
    total = sum(counter_obj.values())
    rows = []
    for label, count in counter_obj.most_common():
        rows.append(
            {
                label_name: label,
                "Games": count,
                "Share %": round((count / total) * 100, 1) if total else 0.0,
            }
        )
    return rows


def compute_streaks(games_desc):
    if not games_desc:
        return {
            "current_label": "None",
            "current_length": 0,
            "longest_win": 0,
            "longest_unbeaten": 0,
        }
    current_result = games_desc[0]["outcome"]
    current_length = 0
    for game in games_desc:
        if game["outcome"] == current_result:
            current_length += 1
        else:
            break
    unbeaten_current = 0
    for game in games_desc:
        if game["outcome"] == "Loss":
            break
        unbeaten_current += 1
    longest_win = 0
    longest_unbeaten = 0
    active_win = 0
    active_unbeaten = 0
    for game in games_desc:
        if game["outcome"] == "Win":
            active_win += 1
            longest_win = max(longest_win, active_win)
        else:
            active_win = 0
        if game["outcome"] != "Loss":
            active_unbeaten += 1
            longest_unbeaten = max(longest_unbeaten, active_unbeaten)
        else:
            active_unbeaten = 0
    return {
        "current_label": current_result,
        "current_length": current_length,
        "current_unbeaten": unbeaten_current,
        "longest_win": longest_win,
        "longest_unbeaten": longest_unbeaten,
    }


def analyze_games(username, profile, stats, games, selected_time_classes=None, start_date=None, end_date=None):
    selected_time_classes = selected_time_classes or []
    rating_rows = extract_rating_snapshot(stats)
    main_rating_label, official_rating = detect_main_format(games, rating_rows)
    by_time = {}
    by_color = {}
    by_phase = {}
    by_length = {}
    by_opening_all = defaultdict(list)
    by_opening_color = {"white": defaultdict(list), "black": defaultdict(list)}
    white_first_moves = defaultdict(list)
    black_responses = defaultdict(list)
    monthly_rows = defaultdict(list)
    loss_reasons = Counter()
    opening_counter = Counter()
    recent_rated = [
        game for game in games
        if game["rated"] and game["opponent_rating"] is not None and game["player_rating"] is not None
    ][:50]

    for game in games:
        by_time.setdefault(game["time_class"], []).append(game)
        by_color.setdefault(game["color"].title(), []).append(game)
        by_phase.setdefault(game["phase"], []).append(game)
        by_length.setdefault(game["length_bucket"], []).append(game)
        if game["opening_family"] != "Unknown":
            by_opening_all[game["opening_family"]].append(game)
            by_opening_color[game["color"]][game["opening_family"]].append(game)
            opening_counter[game["opening_family"]] += 1
        monthly_key = game["ended_at"].strftime("%Y-%m")
        monthly_rows[monthly_key].append(game)

        if game["color"] == "white" and game["white_first_move"]:
            white_first_moves[game["white_first_move"]].append(game)
        if game["color"] == "black" and game["black_response_signature"]:
            black_responses[game["black_response_signature"]].append(game)
        if game["outcome"] == "Loss":
            loss_reasons[game["result_reason"]] += 1

    time_rows = {label: bucket_summary(label, bucket) for label, bucket in by_time.items()}
    color_rows = {label: bucket_summary(label, bucket) for label, bucket in by_color.items()}
    phase_rows = {label: bucket_summary(label, bucket) for label, bucket in by_phase.items()}
    length_rows = {label: bucket_summary(label, bucket) for label, bucket in by_length.items()}
    opening_rows = {label: bucket_summary(label, bucket) for label, bucket in by_opening_all.items()}
    white_opening_rows = {
        label: bucket_summary(label, bucket) for label, bucket in by_opening_color["white"].items()
    }
    black_opening_rows = {
        label: bucket_summary(label, bucket) for label, bucket in by_opening_color["black"].items()
    }
    first_move_rows = {label: bucket_summary(label, bucket) for label, bucket in white_first_moves.items()}
    black_response_rows = {
        label: bucket_summary(label, bucket) for label, bucket in black_responses.items()
    }

    total_games = len(games)
    wins = sum(1 for game in games if game["outcome"] == "Win")
    draws = sum(1 for game in games if game["outcome"] == "Draw")
    losses = total_games - wins - draws
    rated_games = sum(1 for game in games if game["rated"])
    rated_share = (rated_games / total_games) * 100 if total_games else None
    decisive_rate = ((wins + losses) / total_games) * 100 if total_games else None
    draw_rate = (draws / total_games) * 100 if total_games else None
    overall_score = sum(game["score"] for game in games) / total_games if total_games else None
    avg_player = safe_mean([game["player_rating"] for game in games if game["player_rating"] is not None])
    avg_opponent = safe_mean([game["opponent_rating"] for game in games if game["opponent_rating"] is not None])
    avg_accuracy = safe_mean([game["accuracy"] for game in games if game["accuracy"] is not None])
    avg_opp_accuracy = safe_mean(
        [game["opponent_accuracy"] for game in games if game["opponent_accuracy"] is not None]
    )
    avg_moves = safe_mean([game["move_count"] for game in games if game["move_count"] is not None])
    avg_rating_gap = safe_mean(
        [
            game["opponent_rating"] - game["player_rating"]
            for game in games
            if game["player_rating"] is not None and game["opponent_rating"] is not None
        ]
    )
    recent_form_games = games[:10]
    recent_form_score = (
        sum(game["score"] for game in recent_form_games) / len(recent_form_games)
        if recent_form_games
        else None
    )
    recent_rated_score = (
        sum(game["score"] for game in recent_rated) / len(recent_rated) if recent_rated else None
    )
    real_elo = performance_rating(
        safe_mean([game["opponent_rating"] for game in recent_rated if game["opponent_rating"] is not None]),
        recent_rated_score,
    )
    elo_delta = None
    if real_elo is not None and official_rating is not None:
        elo_delta = real_elo - official_rating

    monthly_table = []
    for month_key in sorted(monthly_rows.keys()):
        bucket = monthly_rows[month_key]
        score_pct = sum(game["score"] for game in bucket) / len(bucket) * 100
        monthly_table.append(
            {
                "Month": month_key,
                "Games": len(bucket),
                "Score %": round(score_pct, 1),
                "Band": score_band(score_pct / 100),
                "Avg You": int(round(safe_mean([g["player_rating"] for g in bucket if g["player_rating"] is not None]) or 0))
                if any(g["player_rating"] is not None for g in bucket)
                else None,
                "Avg Opponent": int(round(safe_mean([g["opponent_rating"] for g in bucket if g["opponent_rating"] is not None]) or 0))
                if any(g["opponent_rating"] is not None for g in bucket)
                else None,
            }
        )

    time_ranked = sort_bucket_rows(time_rows, minimum_games=2)
    color_ranked = sort_bucket_rows(color_rows, minimum_games=2)
    phase_ranked = sort_bucket_rows(phase_rows, minimum_games=2)
    length_ranked = sort_bucket_rows(length_rows, minimum_games=2)
    opening_ranked = sort_bucket_rows(opening_rows, minimum_games=2)
    white_opening_ranked = sort_bucket_rows(white_opening_rows, minimum_games=2)
    black_opening_ranked = sort_bucket_rows(black_opening_rows, minimum_games=2)
    first_move_ranked = sort_bucket_rows(first_move_rows, minimum_games=2)
    black_response_ranked = sort_bucket_rows(black_response_rows, minimum_games=2)
    streaks = compute_streaks(games)

    selected_rating_rows = []
    for row in rating_rows:
        time_key = row["format_key"].replace("chess_", "")
        if not selected_time_classes or time_key in selected_time_classes:
            selected_rating_rows.append(row)

    win_games = [game for game in games if game["outcome"] == "Win"]
    loss_games = [game for game in games if game["outcome"] == "Loss"]
    biggest_upset_win = choose_extreme_game(
        win_games,
        key_func=lambda item: (item["gap"], item["opponent_rating"], item["player_rating"]),
        reverse=True,
    )
    highest_rated_win = choose_extreme_game(
        win_games,
        key_func=lambda item: (item["opponent_rating"], item["gap"]),
        reverse=True,
    )
    toughest_opponent = choose_extreme_game(
        games,
        key_func=lambda item: (item["opponent_rating"], item["gap"]),
        reverse=True,
    )
    slip_loss = choose_extreme_game(
        loss_games,
        key_func=lambda item: (item["gap"], item["opponent_rating"]),
        reverse=False,
    )
    best_month = max(monthly_table, key=lambda row: (row["Score %"], row["Games"])) if monthly_table else None
    worst_month = min(monthly_table, key=lambda row: (row["Score %"], -row["Games"])) if monthly_table else None

    style_tags = []
    if avg_moves is not None:
        if avg_moves >= 42:
            style_tags.append("Long-game grinder")
        elif avg_moves <= 24:
            style_tags.append("Fast finisher")
    if draw_rate is not None:
        if draw_rate <= 12:
            style_tags.append("Plays for full points")
        elif draw_rate >= 30:
            style_tags.append("Solid and controlled")
    if time_ranked:
        style_tags.append(f"{pretty_label(time_ranked[0]['label'])} specialist")
    if phase_ranked:
        phase_label = phase_ranked[0]["label"]
        if phase_label == "Opening":
            style_tags.append("Fast starter")
        elif phase_label == "Endgame":
            style_tags.append("Endgame closer")
        else:
            style_tags.append("Middlegame fighter")

    focus_plan = []
    if time_ranked and time_ranked[-1]["games"] >= 3:
        focus_plan.append(
            f"Repair your {pretty_label(time_ranked[-1]['label'])} score first because that is your softest format right now."
        )
    if phase_ranked and phase_ranked[-1]["games"] >= 3:
        focus_plan.append(
            f"Drill {phase_ranked[-1]['label'].lower()} positions for 15 minutes a day to lift your weakest phase."
        )
    if slip_loss:
        focus_plan.append(
            f"Review losses to lower-rated players like the one against {slip_loss['opponent']} to remove preventable points dropped."
        )
    if black_opening_ranked and black_opening_ranked[-1]["games"] >= 3:
        focus_plan.append(
            f"Prepare one safer Black backup against {black_opening_ranked[-1]['label']} structures."
        )

    profile_name = profile.get("name") or profile.get("username") or username
    title = profile.get("title") or ""
    joined = format_epoch(profile.get("joined"))
    country_code = ""
    if isinstance(profile.get("country"), str):
        country_code = profile["country"].rstrip("/").split("/")[-1].upper()

    strengths, weaknesses, advice = generate_coach_notes(
        games=games,
        overall_score=overall_score,
        time_ranked=time_ranked,
        color_ranked=color_ranked,
        phase_ranked=phase_ranked,
        opening_ranked=opening_ranked,
        white_opening_ranked=white_opening_ranked,
        black_opening_ranked=black_opening_ranked,
        recent_form_score=recent_form_score,
        avg_accuracy=avg_accuracy,
        avg_opp_accuracy=avg_opp_accuracy,
        loss_reasons=loss_reasons,
        elo_delta=elo_delta,
        rated_share=rated_share,
        avg_moves=avg_moves,
        biggest_upset_win=biggest_upset_win,
        slip_loss=slip_loss,
        best_month=best_month,
        worst_month=worst_month,
        length_ranked=length_ranked,
    )
    coach_blueprint = build_coach_blueprint(
        profile_name=profile_name,
        total_games=total_games,
        rated_share=rated_share,
        selected_time_classes=selected_time_classes,
        overall_score=overall_score,
        main_rating_label=main_rating_label,
        official_rating=official_rating,
        real_elo=real_elo,
        elo_delta=elo_delta,
        time_ranked=time_ranked,
        color_ranked=color_ranked,
        phase_ranked=phase_ranked,
        length_ranked=length_ranked,
        opening_ranked=opening_ranked,
        white_opening_ranked=white_opening_ranked,
        black_opening_ranked=black_opening_ranked,
        avg_accuracy=avg_accuracy,
        avg_opp_accuracy=avg_opp_accuracy,
        draw_rate=draw_rate,
        decisive_rate=decisive_rate,
        recent_form_score=recent_form_score,
        biggest_upset_win=biggest_upset_win,
        slip_loss=slip_loss,
        toughest_opponent=toughest_opponent,
        best_month=best_month,
        worst_month=worst_month,
        loss_reasons=loss_reasons,
        strengths=strengths,
        weaknesses=weaknesses,
        advice=advice,
    )

    return {
        "username": username,
        "profile_name": profile_name,
        "title": title,
        "country_code": country_code,
        "joined": joined,
        "start_date": start_date,
        "end_date": end_date,
        "date_range_text": format_date_range(start_date, end_date) if start_date and end_date else "",
        "selected_time_classes": selected_time_classes,
        "total_games": total_games,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "rated_games": rated_games,
        "rated_share": rated_share,
        "decisive_rate": decisive_rate,
        "draw_rate": draw_rate,
        "overall_score": overall_score,
        "avg_player": avg_player,
        "avg_opponent": avg_opponent,
        "avg_accuracy": avg_accuracy,
        "avg_opp_accuracy": avg_opp_accuracy,
        "avg_moves": avg_moves,
        "avg_rating_gap": avg_rating_gap,
        "main_rating_label": main_rating_label,
        "official_rating": official_rating,
        "real_elo": real_elo,
        "elo_delta": elo_delta,
        "streaks": streaks,
        "recent_form_score": recent_form_score,
        "rating_rows": selected_rating_rows if selected_time_classes else rating_rows,
        "all_rating_rows": rating_rows,
        "time_ranked": time_ranked,
        "color_ranked": color_ranked,
        "phase_ranked": phase_ranked,
        "length_ranked": length_ranked,
        "opening_ranked": opening_ranked,
        "white_opening_ranked": white_opening_ranked,
        "black_opening_ranked": black_opening_ranked,
        "first_move_ranked": first_move_ranked,
        "black_response_ranked": black_response_ranked,
        "monthly_table": monthly_table,
        "recent_games": games[:18],
        "loss_reasons": loss_reasons,
        "opening_counter": opening_counter,
        "highest_rated_win": highest_rated_win,
        "biggest_upset_win": biggest_upset_win,
        "toughest_opponent": toughest_opponent,
        "slip_loss": slip_loss,
        "best_month": best_month,
        "worst_month": worst_month,
        "style_tags": style_tags[:5],
        "focus_plan": focus_plan[:5],
        "strengths": strengths,
        "weaknesses": weaknesses,
        "advice": advice,
        "coach_blueprint": coach_blueprint,
    }


def generate_coach_notes(
    games,
    overall_score,
    time_ranked,
    color_ranked,
    phase_ranked,
    opening_ranked,
    white_opening_ranked,
    black_opening_ranked,
    recent_form_score,
    avg_accuracy,
    avg_opp_accuracy,
    loss_reasons,
    elo_delta,
    rated_share,
    avg_moves,
    biggest_upset_win,
    slip_loss,
    best_month,
    worst_month,
    length_ranked,
):
    strengths = []
    weaknesses = []
    advice = []

    if time_ranked:
        best_time = time_ranked[0]
        strengths.append(
            f"Best format: {pretty_label(best_time['label'])} with a {best_time['score_pct']:.1f}% score across {best_time['games']} games."
        )
    if color_ranked:
        best_color = color_ranked[0]
        worst_color = color_ranked[-1]
        strengths.append(
            f"Stronger color: {best_color['label']} at {best_color['score_pct']:.1f}% score."
        )
        if worst_color["score_pct"] + 8 < best_color["score_pct"]:
            weaknesses.append(
            f"Color imbalance: {worst_color['label']} is trailing by {(best_color['score_pct'] - worst_color['score_pct']):.1f} score points."
            )
            advice.append(
                f"Spend extra prep on your {worst_color['label']} repertoire so your strong side is not carrying the full result."
            )
    if phase_ranked:
        best_phase = phase_ranked[0]
        worst_phase = phase_ranked[-1]
        if best_phase["games"] >= 3:
            strengths.append(
                f"Best game phase: {best_phase['label']} ({best_phase['score_pct']:.1f}% score)."
            )
        if worst_phase["games"] >= 3 and worst_phase["label"] != best_phase["label"]:
            weaknesses.append(
                f"Drop-off phase: {worst_phase['label']} is your weakest zone at {worst_phase['score_pct']:.1f}%."
            )
    if opening_ranked:
        strengths.append(
            f"Most reliable opening family: {opening_ranked[0]['label']} with {opening_ranked[0]['score_pct']:.1f}% score."
        )
        if opening_ranked[-1]["games"] >= 3 and opening_ranked[-1]["score_pct"] < 45:
            weaknesses.append(
                f"Opening leak: {opening_ranked[-1]['label']} is underperforming at {opening_ranked[-1]['score_pct']:.1f}%."
            )
            advice.append(
                f"Review the first 10 moves in your {opening_ranked[-1]['label']} games and rebuild a simpler plan there."
            )
    if white_opening_ranked:
        strengths.append(
            f"Best White family: {white_opening_ranked[0]['label']} at {white_opening_ranked[0]['score_pct']:.1f}%."
        )
    if black_opening_ranked and black_opening_ranked[-1]["games"] >= 3:
        weakest_black = black_opening_ranked[-1]
        weaknesses.append(
            f"Black-side pressure point: {weakest_black['label']} returns only {weakest_black['score_pct']:.1f}%."
        )
        advice.append(
            f"As Black, aim for structures you score better in than {weakest_black['label']} until that line is repaired."
        )
    if recent_form_score is not None:
        if recent_form_score >= 0.6:
            strengths.append("Recent form is hot over your last 10 games.")
        elif recent_form_score <= 0.4:
            weaknesses.append("Recent form is cold over your last 10 games.")
            advice.append("Reset with slower games, then review the last three losses before grinding more volume.")
    if length_ranked:
        best_length = length_ranked[0]
        strengths.append(
            f"Best game length: {best_length['label'].lower()} games at {best_length['score_pct']:.1f}% score."
        )
    if avg_accuracy is not None and avg_opp_accuracy is not None:
        gap = avg_accuracy - avg_opp_accuracy
        if gap >= 2:
            strengths.append(f"Accuracy edge: you average {gap:.1f} points higher than your opponents.")
        elif gap <= -2:
            weaknesses.append(f"Accuracy gap: opponents average {-gap:.1f} points better.")
            advice.append("Slow down in critical positions and verify forcing lines before you commit.")
    if rated_share is not None and rated_share >= 90:
        strengths.append("Most of your sample is rated play, so this report reflects competitive games, not casual ones.")
    if avg_moves is not None and avg_moves <= 24:
        advice.append("Your games end quickly, so opening accuracy and early tactics will give the biggest rating return.")
    elif avg_moves is not None and avg_moves >= 42:
        strengths.append("You stay composed in longer games and do not rely only on quick tricks.")
    if elo_delta is not None:
        if elo_delta >= 50:
            strengths.append(f"Estimated real Elo is about +{int(round(elo_delta))} above your listed main rating.")
        elif elo_delta <= -50:
            weaknesses.append(f"Estimated real Elo is about {int(round(elo_delta))} below your listed main rating.")
            advice.append("Treat your next block as fundamentals work: openings, tactics, and clock discipline.")
    if biggest_upset_win:
        strengths.append(
            f"Upset ability: you have wins over higher-rated players like {biggest_upset_win['opponent']} ({fmt_delta(biggest_upset_win['gap'])})."
        )
    if slip_loss:
        weaknesses.append(
            f"Point leak: avoidable losses to lower-rated opponents like {slip_loss['opponent']} are holding you back."
        )
        advice.append("Before every move in calm positions, ask what your opponent wants next. That single habit cuts cheap losses.")
    if best_month and worst_month and best_month["Month"] != worst_month["Month"]:
        strengths.append(f"Best month in this sample: {best_month['Month']} at {best_month['Score %']:.1f}% score.")
        weaknesses.append(f"Weakest month in this sample: {worst_month['Month']} at {worst_month['Score %']:.1f}% score.")
    top_loss_reason = loss_reasons.most_common(1)
    if top_loss_reason:
        label, count = top_loss_reason[0]
        if count >= 3 and label in {"Timeout", "Abandoned"}:
            weaknesses.append(f"Clock management is costing games. Top loss reason: {label.lower()}.")
            advice.append("Play one step slower in the opening, then bank time for tactical moments instead of drifting.")
        elif count >= 3 and label in {"Checkmated", "Resigned"}:
            advice.append("Most losses end over the board, so focus on blunder control and practical defense rather than just theory.")
    if overall_score is not None and overall_score < 0.5 and not advice:
        advice.append("Your score is below break-even in this sample, so pick one opening family and one recurring endgame theme to tighten first.")
    return strengths[:7], weaknesses[:7], advice[:7]


def build_coach_blueprint(
    profile_name,
    total_games,
    rated_share,
    selected_time_classes,
    overall_score,
    main_rating_label,
    official_rating,
    real_elo,
    elo_delta,
    time_ranked,
    color_ranked,
    phase_ranked,
    length_ranked,
    opening_ranked,
    white_opening_ranked,
    black_opening_ranked,
    avg_accuracy,
    avg_opp_accuracy,
    draw_rate,
    decisive_rate,
    recent_form_score,
    biggest_upset_win,
    slip_loss,
    toughest_opponent,
    best_month,
    worst_month,
    loss_reasons,
    strengths,
    weaknesses,
    advice,
):
    confidence = confidence_label(total_games, rated_share)
    if elo_delta is not None and elo_delta >= 50:
        headline = f"{profile_name} is performing above the listed {main_rating_label} rating."
    elif overall_score is not None and overall_score >= 0.58:
        headline = f"{profile_name} has a healthy recent score and a stable competitive base."
    elif overall_score is not None and overall_score < 0.45:
        headline = f"{profile_name} is dropping too many practical points, but the weak spots are identifiable."
    else:
        headline = f"{profile_name} looks competitive, with clear areas that can still be sharpened."

    executive_summary = [
        f"Sample size: {total_games} recent games across {selected_class_caption(selected_time_classes or TIME_CLASS_FILTER_OPTIONS)} with {confidence.lower()}.",
        f"Current performance band: {score_band(overall_score)} with a score rate of {fmt_percent((overall_score or 0) * 100) if overall_score is not None else 'N/A'}.",
    ]
    if time_ranked:
        executive_summary.append(
            f"Best environment: {pretty_label(time_ranked[0]['label'])}, where the score is {time_ranked[0]['score_pct']:.1f}%."
        )
    if phase_ranked:
        executive_summary.append(
            f"Biggest structural risk: {phase_ranked[-1]['label'].lower()} play, which is the weakest phase in this sample."
        )
    if elo_delta is not None:
        executive_summary.append(
            f"Real Elo estimate: {fmt_int(real_elo)} versus listed {fmt_int(official_rating)} ({fmt_delta(elo_delta)} difference)."
        )

    priority_ladder = []
    if time_ranked and time_ranked[-1]["games"] >= 3:
        priority_ladder.append(
            f"Priority 1: stabilize {pretty_label(time_ranked[-1]['label'])}, your weakest active rating category."
        )
    if phase_ranked and phase_ranked[-1]["games"] >= 3:
        priority_ladder.append(
            f"Priority 2: train {phase_ranked[-1]['label'].lower()} decisions because that is where results dip."
        )
    if black_opening_ranked and black_opening_ranked[-1]["games"] >= 3:
        priority_ladder.append(
            f"Priority 3: simplify your Black answer against {black_opening_ranked[-1]['label']} structures."
        )
    if slip_loss:
        priority_ladder.append(
            f"Priority 4: remove cheap losses to lower-rated players like {slip_loss['opponent']}."
        )
    if not priority_ladder:
        priority_ladder.append("Priority: keep leaning into your strongest format and review each loss for one repeated mistake.")

    game_plan = []
    if white_opening_ranked:
        game_plan.append(
            f"As White, start from {white_opening_ranked[0]['label']} ideas because that is your most productive family."
        )
    if black_opening_ranked:
        game_plan.append(
            f"As Black, favor your safer structures and avoid drifting into {black_opening_ranked[-1]['label']} when practical alternatives exist."
        )
    if avg_accuracy is not None and avg_opp_accuracy is not None and avg_accuracy < avg_opp_accuracy:
        game_plan.append("Before each committal move, scan checks, captures, and threats once more to cut accuracy leakage.")
    else:
        game_plan.append("Use the opening to reach positions you understand, then press the first imbalance instead of playing automatic moves.")
    if phase_ranked:
        weakest_phase = phase_ranked[-1]["label"]
        if weakest_phase == "Opening":
            game_plan.append("Spend more time in the first 10 moves and refuse rushed opening choices.")
        elif weakest_phase == "Endgame":
            game_plan.append("When better, simplify carefully and convert; when worse, fight for active pieces before swapping.")
        else:
            game_plan.append("In the middlegame, pause before tactical sequences and verify your opponent's best reply.")
    if decisive_rate is not None and decisive_rate > 80:
        game_plan.append("Your games are usually decisive, so practical blunder control will return more rating than passive safety.")

    training_plan = []
    if phase_ranked:
        training_plan.append(
            f"Daily 15 minutes: solve or review {phase_ranked[-1]['label'].lower()} positions from your own games."
        )
    if opening_ranked and opening_ranked[-1]["games"] >= 3:
        training_plan.append(
            f"Daily 15 minutes: rebuild the first 8-10 moves of {opening_ranked[-1]['label']} with one simple plan."
        )
    if time_ranked:
        training_plan.append(
            f"Weekly block: play a focused set of {pretty_label(time_ranked[-1]['label']) if time_ranked else main_rating_label} games and review only the losses."
        )
    if recent_form_score is not None and recent_form_score < 0.5:
        training_plan.append("Short-term reset: play fewer games in a row and review every loss before starting the next batch.")
    if not training_plan:
        training_plan.append("Keep a simple cycle: play, review, extract one lesson, and test it in the next session.")

    review_routine = [
        "After each session, save your three most important mistakes, not every mistake.",
        "Tag each loss by opening, phase, and reason so trends become obvious after 10 games.",
        "Revisit one win too, so you repeat the habits that actually worked.",
    ]
    if loss_reasons.most_common(1):
        review_routine.append(
            f"Special watch: your most common loss reason is {loss_reasons.most_common(1)[0][0].lower()}, so audit that pattern first."
        )

    best_conditions = []
    if time_ranked:
        best_conditions.append(
            f"Best time control: {pretty_label(time_ranked[0]['label'])} ({time_ranked[0]['score_pct']:.1f}% score)."
        )
    if color_ranked:
        best_conditions.append(
            f"Best color: {color_ranked[0]['label']} ({color_ranked[0]['score_pct']:.1f}% score)."
        )
    if length_ranked:
        best_conditions.append(
            f"Best game length: {length_ranked[0]['label'].lower()} games."
        )
    if opening_ranked:
        best_conditions.append(
            f"Most reliable opening family: {opening_ranked[0]['label']}."
        )

    danger_zones = list(weaknesses[:4])
    if not danger_zones and phase_ranked:
        danger_zones.append(
            f"Primary risk zone: {phase_ranked[-1]['label'].lower()} play."
        )
    if slip_loss:
        danger_zones.append(
            f"Practical risk: underperforming against lower-rated opposition."
        )

    narrative = []
    if best_month and worst_month and best_month["Month"] != worst_month["Month"]:
        narrative.append(
            f"Best month: {best_month['Month']} ({best_month['Score %']:.1f}%). Weakest month: {worst_month['Month']} ({worst_month['Score %']:.1f}%)."
        )
    if biggest_upset_win:
        narrative.append(
            f"You can punch above your rating, shown by wins like the one over {biggest_upset_win['opponent']}."
        )
    if toughest_opponent:
        narrative.append(
            f"Strongest opposition faced in this sample: {toughest_opponent['opponent']} ({toughest_opponent['opponent_rating']})."
        )
    narrative.extend(advice[:3])

    return {
        "headline": headline,
        "confidence": confidence,
        "executive_summary": executive_summary[:5],
        "priority_ladder": priority_ladder[:4],
        "game_plan": game_plan[:5],
        "training_plan": training_plan[:5],
        "review_routine": review_routine[:4],
        "best_conditions": best_conditions[:4],
        "danger_zones": danger_zones[:4],
        "narrative": narrative[:5],
    }


def summarize_game(game_payload, username):
    white = game_payload.get("white") or {}
    black = game_payload.get("black") or {}
    pgn = game_payload.get("pgn") or ""
    headers = parse_pgn_headers(pgn)
    moves = extract_moves_from_pgn(pgn)
    normalized_username = normalize_username(username)
    white_username = normalize_username((white.get("username") or ""))
    black_username = normalize_username((black.get("username") or ""))
    is_white = white_username == normalized_username
    player_side = white if is_white else black
    opponent_side = black if is_white else white
    outcome, score = determine_outcome(
        player_side.get("result", ""),
        opponent_side.get("result", ""),
        headers.get("Result", ""),
        is_white,
    )
    end_time = game_payload.get("end_time") or 0
    ply_count = len(moves)
    move_count = math.ceil(ply_count / 2) if ply_count else 0
    game_color = "white" if is_white else "black"
    accuracies = game_payload.get("accuracies") or {}
    opening_name = clean_opening_name(
        headers.get("Opening")
        or game_payload.get("eco")
        or headers.get("ECOUrl")
    )
    white_first_move = moves[0] if moves else ""
    black_response_signature = ""
    if len(moves) > 1:
        black_response_signature = f"vs {moves[0]} -> {moves[1]}"
    return {
        "url": game_payload.get("url", ""),
        "rated": bool(game_payload.get("rated", True)),
        "time_class": (game_payload.get("time_class") or "unknown").lower(),
        "rules": game_payload.get("rules") or "chess",
        "ended_at": datetime.fromtimestamp(int(end_time), tz=timezone.utc),
        "end_time": end_time,
        "color": game_color,
        "outcome": outcome,
        "score": score,
        "player_rating": player_side.get("rating"),
        "opponent_rating": opponent_side.get("rating"),
        "opponent_name": opponent_side.get("username", "Unknown"),
        "result_reason": format_result_reason(player_side.get("result", "")),
        "termination": headers.get("Termination", ""),
        "opening_name": opening_name,
        "opening_family": opening_family(opening_name),
        "opening_tokens": opening_tokens(opening_name),
        "phase": classify_phase(move_count),
        "length_bucket": classify_length(move_count),
        "move_count": move_count,
        "moves": moves,
        "white_first_move": white_first_move,
        "black_response_signature": black_response_signature,
        "signature": move_signature(moves, game_color),
        "accuracy": float(accuracies.get("white" if is_white else "black"))
        if accuracies.get("white" if is_white else "black") is not None
        else None,
        "opponent_accuracy": float(accuracies.get("black" if is_white else "white"))
        if accuracies.get("black" if is_white else "white") is not None
        else None,
    }


def split_pgn_games(pgn_text):
    chunks = re.split(r"(?=\n?\[Event\s+\")", pgn_text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip().startswith("[Event")]


def parse_pgn_rating(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def infer_time_class_from_pgn(headers):
    explicit = (headers.get("TimeClass") or "").strip().lower()
    if explicit in TIME_CLASS_LABELS:
        return explicit
    time_control = (headers.get("TimeControl") or "").strip()
    if not time_control or time_control == "-":
        return "unknown"
    base_text = time_control.split("+")[0]
    try:
        base_seconds = int(base_text)
    except ValueError:
        return "daily" if "/" in time_control else "unknown"
    if base_seconds < 180:
        return "bullet"
    if base_seconds < 600:
        return "blitz"
    if base_seconds < 3600:
        return "rapid"
    return "daily"


def parse_pgn_end_datetime(headers):
    date_text = headers.get("UTCDate") or headers.get("Date") or ""
    time_text = headers.get("UTCTime") or headers.get("Time") or "00:00:00"
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(f"{date_text} {time_text}", fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(tz=timezone.utc)


def determine_pgn_outcome(result_tag, is_white):
    if result_tag == "1-0":
        return ("Win", 1.0) if is_white else ("Loss", 0.0)
    if result_tag == "0-1":
        return ("Loss", 0.0) if is_white else ("Win", 1.0)
    if result_tag == "1/2-1/2":
        return "Draw", 0.5
    return "Draw", 0.5


def summarize_pgn_game(pgn_text, username):
    headers = parse_pgn_headers(pgn_text)
    moves = extract_moves_from_pgn(pgn_text)
    white_name = headers.get("White", "White")
    black_name = headers.get("Black", "Black")
    normalized_username = normalize_username(username)
    white_matches = normalize_username(white_name) == normalized_username
    black_matches = normalize_username(black_name) == normalized_username
    is_white = white_matches or not black_matches
    player_name = white_name if is_white else black_name
    opponent_name = black_name if is_white else white_name
    player_rating = parse_pgn_rating(headers.get("WhiteElo" if is_white else "BlackElo"))
    opponent_rating = parse_pgn_rating(headers.get("BlackElo" if is_white else "WhiteElo"))
    ended_at = parse_pgn_end_datetime(headers)
    outcome, score = determine_pgn_outcome(headers.get("Result", "*"), is_white)
    ply_count = len(moves)
    move_count = math.ceil(ply_count / 2) if ply_count else 0
    game_color = "white" if is_white else "black"
    opening_name = clean_opening_name(headers.get("Opening") or headers.get("ECOUrl") or headers.get("ECO"))
    white_first_move = moves[0] if moves else ""
    black_response_signature = f"vs {moves[0]} -> {moves[1]}" if len(moves) > 1 else ""
    return {
        "url": headers.get("Link", ""),
        "rated": True,
        "time_class": infer_time_class_from_pgn(headers),
        "rules": "chess",
        "ended_at": ended_at,
        "end_time": int(ended_at.timestamp()),
        "color": game_color,
        "outcome": outcome,
        "score": score,
        "player_rating": player_rating,
        "opponent_rating": opponent_rating,
        "opponent_name": opponent_name or "Unknown",
        "result_reason": headers.get("Termination", "PGN result"),
        "termination": headers.get("Termination", ""),
        "opening_name": opening_name,
        "opening_family": opening_family(opening_name),
        "opening_tokens": opening_tokens(opening_name),
        "phase": classify_phase(move_count),
        "length_bucket": classify_length(move_count),
        "move_count": move_count,
        "moves": moves,
        "white_first_move": white_first_move,
        "black_response_signature": black_response_signature,
        "signature": move_signature(moves, game_color),
        "accuracy": None,
        "opponent_accuracy": None,
    }


def load_games_from_pgn(username, pgn_text, selected_time_classes, start_date, end_date, max_games):
    games = []
    for pgn_game in split_pgn_games(pgn_text):
        game = summarize_pgn_game(pgn_game, username)
        game_day = game["ended_at"].date()
        if game_day < start_date or game_day > end_date:
            continue
        if selected_time_classes and game["time_class"] not in selected_time_classes:
            continue
        games.append(game)
    games.sort(key=lambda game: game["end_time"], reverse=True)
    return games[:max_games]


def offline_profile(username):
    return {
        "username": username,
        "name": username,
        "joined": None,
        "country": "",
    }


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_player_bundle(username, start_date, end_date, max_games, rated_only, selected_time_classes):
    normalized_username = normalize_username(username)
    profile = fetch_json_cached(f"https://api.chess.com/pub/player/{quote(normalized_username)}")
    stats = fetch_json_cached(f"https://api.chess.com/pub/player/{quote(normalized_username)}/stats")
    archives_payload = fetch_json_cached(
        f"https://api.chess.com/pub/player/{quote(normalized_username)}/games/archives"
    )
    archives = archives_payload.get("archives") or []
    selected_archives = []
    for archive_url in archives:
        match = re.search(r"/(\d{4})/(\d{2})$", archive_url)
        if not match:
            continue
        year_value = int(match.group(1))
        month_value = int(match.group(2))
        if month_overlaps_range(year_value, month_value, start_date, end_date):
            selected_archives.append(archive_url)
    selected_archives = list(reversed(selected_archives))
    collected = []
    for archive_url in selected_archives:
        archive_payload = fetch_json_cached(archive_url)
        for game_payload in reversed(archive_payload.get("games") or []):
            if (game_payload.get("rules") or "chess") != "chess":
                continue
            if rated_only and not bool(game_payload.get("rated", True)):
                continue
            time_class = (game_payload.get("time_class") or "unknown").lower()
            if selected_time_classes and time_class not in selected_time_classes:
                continue
            white = game_payload.get("white") or {}
            black = game_payload.get("black") or {}
            usernames = {normalize_username(white.get("username", "")), normalize_username(black.get("username", ""))}
            if normalized_username not in usernames:
                continue
            game_summary = summarize_game(game_payload, normalized_username)
            game_day = game_summary["ended_at"].date()
            if game_day < start_date or game_day > end_date:
                continue
            collected.append(game_summary)
            if len(collected) >= max_games:
                break
        if len(collected) >= max_games:
            break
    collected.sort(key=lambda game: game["end_time"], reverse=True)
    return profile, stats, collected


def score_badge_class(outcome):
    if outcome == "Win":
        return "good"
    if outcome == "Loss":
        return "warn"
    return ""


def render_chip(text, kind=""):
    class_name = f"chip {kind}".strip()
    return f'<span class="{class_name}">{html.escape(text)}</span>'


def render_hero(summary):
    chips = [
        render_chip(summary["main_rating_label"]),
        render_chip(f"{summary['total_games']} recent games"),
        render_chip(selected_class_caption(summary["selected_time_classes"] or TIME_CLASS_FILTER_OPTIONS)),
    ]
    if summary["country_code"]:
        chips.append(render_chip(summary["country_code"]))
    if summary["title"]:
        chips.append(render_chip(summary["title"]))
    for style_tag in summary.get("style_tags", [])[:3]:
        chips.append(render_chip(style_tag, "good"))
    st.markdown(
        f"""
        <div class="hero-panel">
            <div class="eyebrow">Public Chess.com Intelligence</div>
            <div class="hero-title">{html.escape(summary['profile_name'])}</div>
            <div class="hero-copy">
                Deep profile scan for <strong>{html.escape(summary['username'])}</strong>.
                This dashboard mines recent public games, rating snapshots, opening habits,
                streak data, rating-category results, and live position suggestions to build a practical coaching report.
            </div>
            <div class="chip-row">{''.join(chips)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label, value, note):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{html.escape(label)}</div>
            <div class="metric-value">{html.escape(value)}</div>
            <div class="metric-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight_banner(title, text, chips=None):
    chip_html = "".join(render_chip(chip, "good") for chip in (chips or []))
    st.markdown(
        f"""
        <div class="insight-banner">
            <div class="insight-title">{html.escape(title)}</div>
            <div class="insight-copy">{html.escape(text)}</div>
            <div class="chip-row">{chip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_text_card(title, items, good=False):
    chip_kind = "good" if good else "warn"
    body = "".join(render_chip(item, chip_kind) for item in items) if items else render_chip("Not enough data yet")
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{html.escape(title)}</div>
            <div class="section-copy">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_list_card(title, items, tone="neutral", ordered=False, intro=None):
    items = items or ["Not enough data yet."]
    tag = "ol" if ordered else "ul"
    list_html = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    intro_html = f'<div class="section-copy">{html.escape(intro)}</div>' if intro else ""
    st.markdown(
        f"""
        <div class="list-card {html.escape(tone)}">
            <div class="section-title">{html.escape(title)}</div>
            {intro_html}
            <{tag}>{list_html}</{tag}>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_fact_grid(title, facts):
    if not facts:
        return
    parts = []
    for label, value in facts:
        parts.append(
            f"""
            <div class="fact-item">
                <div class="fact-label">{html.escape(label)}</div>
                <div class="fact-value">{html.escape(value)}</div>
            </div>
            """
        )
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{html.escape(title)}</div>
            <div class="fact-grid">{''.join(parts)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_runtime_error(exc):
    message = str(exc)
    headline, _, detail = message.partition("\n\n")
    st.error(headline)
    if detail:
        with st.expander("What to try"):
            st.markdown(detail)


def render_summary_metrics(summary):
    streak_label = (
        f"{summary['streaks']['current_length']} {summary['streaks']['current_label'].lower()}"
        if summary["streaks"]["current_length"]
        else "No streak"
    )
    current_score = summary["overall_score"] * 100 if summary["overall_score"] is not None else None
    real_elo_text = fmt_int(summary["real_elo"]) if summary["real_elo"] is not None else "N/A"
    elo_note = "Estimated from recent rated opposition."
    if summary["elo_delta"] is not None:
        if summary["elo_delta"] >= 0:
            elo_note = f"About +{int(round(summary['elo_delta']))} versus listed {summary['main_rating_label']} rating."
        else:
            elo_note = f"About {int(round(summary['elo_delta']))} versus listed {summary['main_rating_label']} rating."
    row1 = st.columns(3)
    with row1[0]:
        render_metric_card(
            "Official Rating",
            fmt_int(summary["official_rating"]),
            f"Main format: {summary['main_rating_label']}. Joined {summary['joined']}.",
        )
    with row1[1]:
        render_metric_card(
            "Estimated Real Elo",
            real_elo_text,
            elo_note,
        )
    with row1[2]:
        render_metric_card(
            "Score Rate",
            fmt_percent(current_score),
            f"{summary['wins']}W / {summary['draws']}D / {summary['losses']}L in the loaded sample.",
        )

    row2 = st.columns(3)
    with row2[0]:
        render_metric_card(
            "Average Accuracy",
            fmt_percent(summary["avg_accuracy"]),
            "Average move quality from available Chess.com game reports.",
        )
    with row2[1]:
        render_metric_card(
            "Average Opponent",
            fmt_int(summary["avg_opponent"]),
            f"Average own rating {fmt_int(summary['avg_player'])}. Rated sample {fmt_percent(summary['rated_share'])}.",
        )
    with row2[2]:
        render_metric_card(
            "Current Streak",
            streak_label,
            f"Longest win streak: {summary['streaks']['longest_win']}. Avg moves {fmt_int(summary['avg_moves'])}.",
        )


def prepare_recent_games_table(games):
    rows = []
    for game in games:
        rows.append(
            {
                "Date": game["ended_at"].strftime("%Y-%m-%d"),
                "Result": game["outcome"],
                "Color": game["color"].title(),
                "Format": pretty_label(game["time_class"]),
                "Opponent": game["opponent_name"],
                "Opp Rating": game["opponent_rating"],
                "Opening": game["opening_family"],
                "Moves": game["move_count"],
                "Loss Reason": game["result_reason"] if game["outcome"] == "Loss" else "",
            }
        )
    return rows


def prepare_rating_table(rows):
    table = []
    for row in rows:
        table.append(
            {
                "Format": row["label"],
                "Current": row["last"],
                "Peak": row["best"],
                "Tracked Games": row["games"],
            }
        )
    return table


def render_event_card(title, event, empty_text):
    if not event:
        st.markdown(
            f"""
            <div class="section-card">
                <div class="section-title">{html.escape(title)}</div>
                <div class="section-copy">{html.escape(empty_text)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    details = [
        f"{event['date']} vs {event['opponent']}",
        f"{event['format']} | {event['opening']}",
        f"You {event['player_rating']} vs Opp {event['opponent_rating']}",
        f"Gap: {fmt_delta(event['gap'])}",
    ]
    body = "".join(render_chip(item, "good" if event["result"] == "Win" else "warn") for item in details)
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{html.escape(title)}</div>
            <div class="section-copy">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_row_by_label(rows, label):
    for row in rows:
        if row["label"] == label:
            return row
    return None


def build_top_dashboard(summary):
    white_row = get_row_by_label(summary["color_ranked"], "White")
    black_row = get_row_by_label(summary["color_ranked"], "Black")
    timeout_count = sum(
        count for reason, count in summary["loss_reasons"].items() if reason in {"Timeout", "Abandoned"}
    )
    timeout_rate = (timeout_count / summary["total_games"]) * 100 if summary["total_games"] else 0
    accuracy_gap = 0
    if summary["avg_accuracy"] is not None and summary["avg_opp_accuracy"] is not None:
        accuracy_gap = summary["avg_accuracy"] - summary["avg_opp_accuracy"]
    opening_total = sum(summary["opening_counter"].values())
    top_opening_share = (
        summary["opening_counter"].most_common(1)[0][1] / opening_total * 100
        if opening_total
        else 0
    )
    top_three_share = (
        sum(count for _, count in summary["opening_counter"].most_common(3)) / opening_total * 100
        if opening_total
        else 0
    )
    recent_losses = sum(1 for game in summary["recent_games"][:8] if game["outcome"] == "Loss")
    recent_loss_rate = (recent_losses / min(len(summary["recent_games"][:8]), 8) * 100) if summary["recent_games"][:8] else 0
    attack = clamp(
        ((white_row["score_pct"] if white_row else (summary["overall_score"] or 0.5) * 100) * 0.62)
        + ((summary["decisive_rate"] or 50) * 0.12)
        + max(0, accuracy_gap) * 2.4
        + (6 if summary["phase_ranked"] and summary["phase_ranked"][0]["label"] in {"Opening", "Middlegame"} else 0)
    )
    defense = clamp(
        ((black_row["score_pct"] if black_row else (summary["overall_score"] or 0.5) * 100) * 0.62)
        + ((100 - timeout_rate) * 0.18)
        + (8 if summary["phase_ranked"] and summary["phase_ranked"][0]["label"] == "Endgame" else 0)
        - max(0, -accuracy_gap) * 1.6
    )
    time_score = clamp(
        78
        - timeout_rate * 1.15
        + ((summary["recent_form_score"] or summary["overall_score"] or 0.5) - 0.5) * 30
        - max(0, (summary["avg_moves"] or 30) - 40) * 0.35
    )
    mind_score = clamp(
        ((summary["recent_form_score"] or summary["overall_score"] or 0.5) * 60)
        + ((summary["overall_score"] or 0.5) * 35)
        - recent_loss_rate * 0.25
        - (8 if summary["slip_loss"] else 0)
    )
    overall_rating = clamp(
        (attack + defense + time_score + mind_score) / 4 + ((summary["elo_delta"] or 0) / 14),
        1,
        99,
    )

    time_trouble = clamp(timeout_rate * 2.8)
    tilts_easily = clamp(recent_loss_rate * 1.15 + (12 if summary["streaks"]["current_label"] == "Loss" else 0))
    limited_repertoire = clamp(top_opening_share * 0.95 + (20 if len(summary["opening_counter"]) <= 4 and opening_total else 0))
    repetitive_patterns = clamp(top_three_share * 0.7 + (15 if top_opening_share >= 35 else 0))
    stalker_score = round((time_trouble + tilts_easily + limited_repertoire + repetitive_patterns) / 4)
    predictability = clamp((limited_repertoire * 0.6) + (repetitive_patterns * 0.4))
    if predictability < 35:
        predictability_label = "Predictability Low"
    elif predictability < 60:
        predictability_label = "Predictability Medium"
    else:
        predictability_label = "Predictability High"

    if summary["streaks"]["current_length"] >= 3 and summary["streaks"]["current_label"] == "Win":
        badge = "The Streaker"
    elif (summary["elo_delta"] or 0) >= 50:
        badge = "The Climber"
    elif summary["phase_ranked"] and summary["phase_ranked"][0]["label"] == "Endgame":
        badge = "The Closer"
    else:
        badge = "The Grinder"

    return {
        "badge": badge,
        "overall": round(overall_rating),
        "attack": round(attack),
        "defense": round(defense),
        "time": round(time_score),
        "mind": round(mind_score),
        "stalker_score": stalker_score,
        "predictability_label": predictability_label,
        "risk_rows": [
            ("Time trouble", round(time_trouble), "safe"),
            ("Tilts easily", round(tilts_easily), "warn"),
            ("Limited repertoire", round(limited_repertoire), "safe"),
            ("Repetitive patterns", round(repetitive_patterns), "safe"),
        ],
    }


def render_top_dashboard(summary):
    deck = build_top_dashboard(summary)
    selected_ratings = []
    rating_lookup = {row["label"]: row["last"] for row in summary["all_rating_rows"] if row.get("last") is not None}
    for option in summary["selected_time_classes"] or TIME_CLASS_FILTER_OPTIONS:
        label = pretty_label(option)
        if label in rating_lookup:
            selected_ratings.append((label, rating_lookup[label]))
    if not selected_ratings:
        selected_ratings = [(row["label"], row["last"]) for row in summary["rating_rows"][:4] if row.get("last") is not None]
    if not selected_ratings and summary.get("official_rating") is not None:
        selected_ratings = [(summary["main_rating_label"], summary["official_rating"])]

    initials = (summary["username"][:1] or "?").upper()
    stat_rows_html = []
    for label, score in [
        ("ATK", deck["attack"]),
        ("DEF", deck["defense"]),
        ("TIME", deck["time"]),
        ("MIND", deck["mind"]),
    ]:
        stat_rows_html.append(
            f"""
            <div class="mini-stat">
                <div class="mini-value">{score}</div>
                <div class="mini-label">{label}</div>
                <div class="mini-bar"><span style="width:{score}%;"></span></div>
            </div>
            """
        )

    rating_tiles_html = []
    for label, rating_value in selected_ratings[:4]:
        rating_tiles_html.append(
            f"""
            <div class="rating-pill">
                <span>{html.escape(label)}</span>
                <strong>{fmt_int(rating_value)}</strong>
            </div>
            """
        )

    risk_rows_html = []
    risk_colors = {
        "safe": "#28a38c",
        "warn": "#e69527",
    }
    for label, value, tone in deck["risk_rows"]:
        risk_rows_html.append(
            f"""
            <div class="risk-row">
                <div class="risk-top">
                    <span>{html.escape(label)}</span>
                    <strong>{value}</strong>
                </div>
                <div class="risk-bar"><span style="width:{value}%; background:{risk_colors.get(tone, '#28a38c')};"></span></div>
            </div>
            """
        )

    st.markdown(
        f"""
        <div class="summary-deck">
            <div class="summary-card summary-left">
                <div class="summary-head">
                    <div class="avatar-box">{html.escape(initials)}</div>
                    <div class="identity-box">
                        <div class="identity-name">{html.escape(summary['username'])}</div>
                        <div class="identity-badge">{html.escape(deck['badge'])}</div>
                        <div class="identity-range">
                            {summary['total_games']} Games · {html.escape(selected_class_caption(summary['selected_time_classes'] or TIME_CLASS_FILTER_OPTIONS))} · {html.escape(summary['date_range_text'])}
                        </div>
                    </div>
                    <div class="ovr-box">
                        <div class="ring" style="--progress:{deck['overall']};">
                            <div class="ring-inner">
                                <span>OVR</span>
                                <strong>{deck['overall']}</strong>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="mini-grid">{''.join(stat_rows_html)}</div>
                <div class="rating-grid">{''.join(rating_tiles_html)}</div>
                <div class="summary-footer">
                    <div class="summary-tag">{score_band(summary['overall_score'])}</div>
                    <div class="summary-record">
                        <span class="win">{summary['wins']}W</span>
                        <span>{summary['draws']}D</span>
                        <span class="loss">{summary['losses']}L</span>
                    </div>
                </div>
            </div>
            <div class="summary-card summary-right">
                <div class="summary-title-row">
                    <div class="summary-title">Stalker Score</div>
                    <div class="summary-predict">{html.escape(deck['predictability_label'])}</div>
                </div>
                <div class="stalker-layout">
                    <div class="stalker-ring">
                        <div class="ring ring-teal" style="--progress:{deck['stalker_score']};">
                            <div class="ring-inner">
                                <strong>{deck['stalker_score']}</strong>
                                <span>/100</span>
                            </div>
                        </div>
                    </div>
                    <div class="stalker-risks">{''.join(risk_rows_html)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def best_opening_overlap(user_rows, opponent_rows):
    best_match = None
    for user_row in user_rows[:6]:
        user_tokens = opening_tokens(user_row["label"])
        for opponent_row in opponent_rows[:6]:
            opponent_tokens = opening_tokens(opponent_row["label"])
            overlap = user_tokens & opponent_tokens
            if not overlap:
                continue
            score = user_row["score_pct"] - opponent_row["score_pct"] + len(overlap) * 5
            if best_match is None or score > best_match["score"]:
                best_match = {
                    "user_row": user_row,
                    "opponent_row": opponent_row,
                    "overlap": overlap,
                    "score": score,
                }
    return best_match


def build_matchup_report(user_summary, opponent_summary):
    report = []
    opponent_worst_time = opponent_summary["time_ranked"][-1] if opponent_summary["time_ranked"] else None
    user_best_time = user_summary["time_ranked"][0] if user_summary["time_ranked"] else None
    if opponent_worst_time and user_best_time and opponent_worst_time["label"] == user_best_time["label"]:
        report.append(
            f"Format edge: you are strongest in {pretty_label(user_best_time['label'])}, and {opponent_summary['profile_name']} is weakest there."
        )

    white_plan = best_opening_overlap(
        user_summary["white_opening_ranked"],
        opponent_summary["black_opening_ranked"][::-1],
    )
    if white_plan:
        report.append(
            f"As White, steer toward {white_plan['user_row']['label']}. You score {white_plan['user_row']['score_pct']:.1f}% there, while {opponent_summary['profile_name']} scores only {white_plan['opponent_row']['score_pct']:.1f}% from the Black side."
        )
    elif opponent_summary["black_opening_ranked"]:
        weak_black = opponent_summary["black_opening_ranked"][-1]
        report.append(
            f"As White, look for ways to drag the game toward {weak_black['label']}, which is one of {opponent_summary['profile_name']}'s weakest Black families."
        )

    black_plan = None
    opponent_first_move = opponent_summary["first_move_ranked"][0]["label"] if opponent_summary["first_move_ranked"] else ""
    if opponent_first_move:
        candidates = [
            row for row in user_summary["black_response_ranked"] if row["label"].startswith(f"vs {opponent_first_move} ->")
        ]
        if candidates:
            black_plan = candidates[0]
    if black_plan:
        report.append(
            f"As Black against {opponent_first_move}, your best recorded reply is {black_plan['label'].replace('vs ', '')} with a {black_plan['score_pct']:.1f}% score."
        )
    elif opponent_first_move:
        report.append(
            f"{opponent_summary['profile_name']} most often starts with {opponent_first_move}, so prep one calm, well-known answer there before playing."
        )

    opponent_weak_phase = opponent_summary["phase_ranked"][-1] if opponent_summary["phase_ranked"] else None
    if opponent_weak_phase:
        if opponent_weak_phase["label"] == "Opening":
            report.append("Pressure early. Their weakest phase is the opening, so ask immediate concrete questions.")
        elif opponent_weak_phase["label"] == "Endgame":
            report.append("Simplify confidently if the position allows it. Their weakest phase is the endgame.")
        else:
            report.append("Keep the middle game messy and force decisions. Their weakest phase is the middlegame.")

    top_loss_reason = opponent_summary["loss_reasons"].most_common(1)
    if top_loss_reason:
        reason, count = top_loss_reason[0]
        if count >= 3:
            report.append(
                f"Recurring problem: {opponent_summary['profile_name']} loses often by {reason.lower()}, so practical pressure matters."
            )

    if not report:
        report.append("Not enough shared data for a sharp matchup read, so rely on your strongest time control and your most stable opening family.")
    return report[:5]


def parse_fen_board(fen):
    parts = fen.strip().split()
    if len(parts) < 4:
        raise ValueError("FEN must include board, side to move, castling rights, and en passant square.")
    board_part = parts[0]
    ranks = board_part.split("/")
    if len(ranks) != 8:
        raise ValueError("FEN board must have 8 ranks.")
    board = []
    for rank_text in ranks:
        row = []
        for char in rank_text:
            if char.isdigit():
                row.extend([""] * int(char))
            elif char in PIECE_MAP:
                row.append(char)
            else:
                raise ValueError("FEN contains an unknown piece symbol.")
        if len(row) != 8:
            raise ValueError("Each FEN rank must contain exactly 8 files.")
        board.append(row)
    return {
        "board": board,
        "turn": "White" if parts[1] == "w" else "Black",
        "castling": parts[2],
        "en_passant": parts[3],
    }


def square_to_coords(square_name):
    file_index = ord(square_name[0]) - ord("a")
    rank_index = 8 - int(square_name[1])
    return rank_index, file_index


def render_board(fen, best_move=None):
    parsed = parse_fen_board(fen)
    highlights = set()
    if best_move and len(best_move) >= 4:
        highlights.add(best_move[:2])
        highlights.add(best_move[2:4])
    files = "abcdefgh"
    board_html = ['<div class="board-shell"><div class="board-grid">']
    for rank_index, row in enumerate(parsed["board"]):
        for file_index, piece in enumerate(row):
            square_name = f"{files[file_index]}{8 - rank_index}"
            classes = ["square"]
            classes.append("sq-light" if (rank_index + file_index) % 2 == 0 else "sq-dark")
            if square_name in highlights:
                classes.append("sq-highlight")
            coord = square_name if rank_index == 7 or file_index == 0 else ""
            board_html.append(
                f'<div class="{" ".join(classes)}">{PIECE_MAP.get(piece, "")}<span class="coord">{coord}</span></div>'
            )
    board_html.append("</div></div>")
    st.markdown("".join(board_html), unsafe_allow_html=True)
    st.caption(
        f"Turn: {parsed['turn']} | Castling: {parsed['castling']} | En passant: {parsed['en_passant']}"
    )


@st.cache_data(ttl=900, show_spinner=False)
def fetch_cloud_eval(fen, multi_pv):
    query = urlencode({"fen": fen, "multiPv": multi_pv})
    return request_json(f"https://lichess.org/api/cloud-eval?{query}")


def render_overview_tab(summary):
    blueprint = summary["coach_blueprint"]
    render_insight_banner(
        "30-Second Verdict",
        blueprint["headline"],
        [
            blueprint["confidence"],
            selected_class_caption(summary["selected_time_classes"] or TIME_CLASS_FILTER_OPTIONS),
            f"{summary['total_games']} games",
        ],
    )

    render_fact_grid(
        "Quick Read",
        [
            ("Official Rating", fmt_int(summary["official_rating"])),
            ("Estimated Real Elo", fmt_int(summary["real_elo"])),
            ("Score Rate", fmt_percent((summary["overall_score"] or 0) * 100) if summary["overall_score"] is not None else "N/A"),
            ("Best Format", pretty_label(summary["time_ranked"][0]["label"]) if summary["time_ranked"] else "N/A"),
            ("Weakest Phase", summary["phase_ranked"][-1]["label"] if summary["phase_ranked"] else "N/A"),
            ("Confidence", blueprint["confidence"]),
        ],
    )

    left, right = st.columns(2)
    with left:
        render_list_card("Executive Summary", blueprint["executive_summary"], tone="neutral")
        render_list_card("Priority Ladder", blueprint["priority_ladder"], tone="warn", ordered=True)
    with right:
        render_list_card("Strengths", summary["strengths"], tone="good")
        render_list_card("Danger Zones", blueprint["danger_zones"], tone="warn")

    coach_left, coach_right = st.columns(2)
    with coach_left:
        render_list_card("Best Conditions", blueprint["best_conditions"], tone="good")
        render_list_card("Focus Plan", summary["focus_plan"] or ["Keep building on your strongest format and opening family."], tone="neutral")
    with coach_right:
        render_list_card("Practical Advice", summary["advice"] or ["Keep repeating your best format and best opening family."], tone="neutral")
        render_list_card("Story From The Data", blueprint["narrative"], tone="neutral")

    spot1, spot2, spot3 = st.columns(3)
    with spot1:
        render_event_card("Best Win", summary["highest_rated_win"], "No rated win detail available yet.")
    with spot2:
        render_event_card("Biggest Upset", summary["biggest_upset_win"], "No upset win found in this sample.")
    with spot3:
        render_event_card("Biggest Leak", summary["slip_loss"], "No lower-rated loss stood out in this sample.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Time-Control Breakdown")
        st.dataframe(bucket_to_detail_table(summary["time_ranked"], limit=8), use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### Monthly Trend")
        st.dataframe(summary["monthly_table"], use_container_width=True, hide_index=True)


def render_blueprint_tab(summary):
    blueprint = summary["coach_blueprint"]
    left, right = st.columns(2)
    with left:
        render_list_card("Game-Day Plan", blueprint["game_plan"], tone="neutral", ordered=True)
        render_list_card("Training Plan", blueprint["training_plan"], tone="good", ordered=True)
    with right:
        render_list_card("Review Routine", blueprint["review_routine"], tone="neutral", ordered=True)
        render_list_card("Weaknesses To Watch", summary["weaknesses"] or ["No major weakness stood out in this sample."], tone="warn")


def render_formats_tab(summary):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Selected Rating Categories")
        rating_table = prepare_rating_table(summary["rating_rows"])
        if rating_table:
            st.dataframe(rating_table, use_container_width=True, hide_index=True)
        else:
            st.info("No official rating categories were available for this filter.")
        st.markdown("### Phase Breakdown")
        st.dataframe(bucket_to_detail_table(summary["phase_ranked"], limit=6), use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### Color Split")
        st.dataframe(bucket_to_detail_table(summary["color_ranked"], limit=4), use_container_width=True, hide_index=True)
        st.markdown("### Game Length Profile")
        st.dataframe(bucket_to_detail_table(summary["length_ranked"], limit=4), use_container_width=True, hide_index=True)

    lower1, lower2 = st.columns(2)
    with lower1:
        st.markdown("### Opening Families")
        st.dataframe(bucket_to_detail_table(summary["opening_ranked"], limit=10), use_container_width=True, hide_index=True)
    with lower2:
        st.markdown("### Loss Reasons")
        loss_reason_table = counter_to_table(summary["loss_reasons"], "Reason")
        if loss_reason_table:
            st.dataframe(loss_reason_table, use_container_width=True, hide_index=True)
        else:
            st.info("No losses in this sample, so there are no loss reasons to display.")


def render_profile_tab(summary):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### White Repertoire")
        st.dataframe(bucket_to_detail_table(summary["white_opening_ranked"], limit=8), use_container_width=True, hide_index=True)
        st.markdown("### Favorite First Moves")
        st.dataframe(bucket_to_detail_table(summary["first_move_ranked"], limit=8), use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### Black Repertoire")
        st.dataframe(bucket_to_detail_table(summary["black_opening_ranked"], limit=8), use_container_width=True, hide_index=True)
        st.markdown("### Best Black Replies")
        st.dataframe(bucket_to_detail_table(summary["black_response_ranked"], limit=8), use_container_width=True, hide_index=True)

    st.markdown("### Recent Games")
    st.dataframe(prepare_recent_games_table(summary["recent_games"]), use_container_width=True, hide_index=True)


def render_opponent_tab(user_summary):
    if not analysis_is_compatible(st.session_state.get("opponent_summary")) and st.session_state.get("opponent_summary") is not None:
        st.session_state["opponent_summary"] = None

    st.markdown(
        """
        <div class="glass-card">
            <div class="section-title">Opponent Prep</div>
            <div class="section-copy">
                Enter another public Chess.com username and this app will compare their openings,
                weakest phases, streaks, and format preferences against your profile.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("opponent_form"):
        opponent_username = st.text_input(
            "Opponent Chess.com username",
            value=st.session_state.get("opponent_username", ""),
            placeholder="for example: gothamchess",
        )
        prep_clicked = st.form_submit_button("Build Matchup Report", use_container_width=True)

    if prep_clicked and opponent_username.strip():
        st.session_state["opponent_username"] = opponent_username.strip()
        try:
            with st.spinner(f"Scanning {opponent_username.strip()} ..."):
                profile, stats, games = fetch_player_bundle(
                    opponent_username.strip(),
                    st.session_state.get("start_date", date.today() - timedelta(days=DEFAULT_RANGE_DAYS)),
                    st.session_state.get("end_date", date.today()),
                    min(st.session_state.get("max_games", DEFAULT_MAX_GAMES), 120),
                    st.session_state.get("rated_only", True),
                    st.session_state.get("selected_time_classes", DEFAULT_TIME_CLASS_FILTERS),
                )
            if not games:
                st.session_state["opponent_summary"] = None
                st.warning("No public standard games were found for that player in the selected range.")
            else:
                st.session_state["opponent_summary"] = analyze_games(
                    opponent_username.strip(),
                    profile,
                    stats,
                    games,
                    st.session_state.get("selected_time_classes", DEFAULT_TIME_CLASS_FILTERS),
                    st.session_state.get("start_date", date.today() - timedelta(days=DEFAULT_RANGE_DAYS)),
                    st.session_state.get("end_date", date.today()),
                )
        except RuntimeError as exc:
            st.session_state["opponent_summary"] = None
            show_runtime_error(exc)

    opponent_summary = st.session_state.get("opponent_summary")
    if not opponent_summary:
        st.info("Load an opponent profile to unlock the matchup advice.")
        return

    report = build_matchup_report(user_summary, opponent_summary)
    cols = st.columns(3)
    with cols[0]:
        st.metric("Opponent Official Rating", fmt_int(opponent_summary["official_rating"]))
    with cols[1]:
        st.metric("Opponent Real Elo", fmt_int(opponent_summary["real_elo"]))
    with cols[2]:
        st.metric(
            "Opponent Streak",
            f"{opponent_summary['streaks']['current_length']} {opponent_summary['streaks']['current_label'].lower()}",
        )

    render_text_card("How To Beat This Opponent", report, good=True)

    left, right = st.columns(2)
    with left:
        st.markdown("### Opponent Opening Families")
        st.dataframe(top_rows_as_table(opponent_summary["opening_ranked"], limit=8), use_container_width=True, hide_index=True)
    with right:
        st.markdown("### Opponent Weak Spots")
        weakness_rows = top_rows_as_table(list(reversed(opponent_summary["phase_ranked"])), limit=3)
        weakness_rows.extend(top_rows_as_table(list(reversed(opponent_summary["time_ranked"])), limit=3))
        st.dataframe(weakness_rows, use_container_width=True, hide_index=True)


def render_position_tab():
    st.markdown(
        """
        <div class="glass-card">
            <div class="section-title">Position Lab</div>
            <div class="section-copy">
                Paste any FEN and CHESSTALKER Pro will try to pull the strongest cached moves from Lichess cloud evaluation.
                If the position is rare, the API may not have a stored answer yet.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("fen_form"):
        fen_value = st.text_area(
            "FEN position",
            value=st.session_state.get("fen_value", START_FEN),
            height=110,
        )
        multi_pv = st.slider("How many candidate lines", 1, 5, DEFAULT_MULTI_PV)
        fen_clicked = st.form_submit_button("Analyze Position", use_container_width=True)

    chosen_move = None
    if fen_clicked:
        st.session_state["fen_value"] = fen_value.strip()
        st.session_state["fen_multi_pv"] = multi_pv
        try:
            parse_fen_board(fen_value.strip())
            with st.spinner("Fetching cloud evaluation..."):
                st.session_state["fen_eval"] = fetch_cloud_eval(fen_value.strip(), multi_pv)
        except ValueError as exc:
            st.session_state["fen_eval"] = None
            st.error(str(exc))
        except RuntimeError as exc:
            st.session_state["fen_eval"] = None
            show_runtime_error(exc)

    eval_payload = st.session_state.get("fen_eval")
    current_fen = st.session_state.get("fen_value", START_FEN)
    if eval_payload and (eval_payload.get("pvs") or []):
        chosen_move = eval_payload["pvs"][0].get("moves", "").split(" ")[0]
    try:
        render_board(current_fen, chosen_move)
    except ValueError:
        render_board(START_FEN, None)
        st.caption("Showing the start position because the current FEN is invalid.")

    if not eval_payload:
        st.info("Analyze a position to get best-move suggestions.")
        return
    pvs = eval_payload.get("pvs") or []
    if not pvs:
        st.warning("No cached evaluation was available for this position yet.")
        return

    rows = []
    for index, pv in enumerate(pvs, start=1):
        move_tokens = (pv.get("moves") or "").split()
        first_move = move_tokens[0] if move_tokens else ""
        if pv.get("mate") is not None:
            eval_text = f"Mate in {pv.get('mate')}"
        elif pv.get("cp") is not None:
            eval_text = f"{pv.get('cp') / 100:.2f}"
        else:
            eval_text = "N/A"
        rows.append(
            {
                "Line": index,
                "Best Move": uci_to_text(first_move),
                "Eval": eval_text,
                "Continuation": " ".join(uci_to_text(token) for token in move_tokens[:5]),
            }
        )
    st.markdown("### Best Moves")
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        f"Depth: {eval_payload.get('depth', 'N/A')} | Nodes: {eval_payload.get('knodes', 'N/A')}k | Best move highlighted on the board."
    )


def render_empty_state():
    st.markdown(
        """
        <div class="hero-panel">
            <div class="eyebrow">Professional Chess Dashboard</div>
            <div class="hero-title">Analyze a Chess.com profile like a serious coach.</div>
            <div class="hero-copy">
                Enter a real Chess.com username in the sidebar to unlock ratings, streaks,
                opening DNA, category-specific Elo analysis, an organized coaching blueprint, opponent prep, and a live position lab.
            </div>
            <div class="chip-row">
                <span class="chip">Real Elo estimate</span>
                <span class="chip">Choose 1-5 categories</span>
                <span class="chip">Executive summary</span>
                <span class="chip">Strengths & weaknesses</span>
                <span class="chip">Opponent scout</span>
                <span class="chip">Best move from FEN</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Simple Workflow</div>
            <div class="section-copy">
                1. Pick a public Chess.com username.
                2. Choose the rating categories you care about, like Blitz, Rapid, Bullet, or Daily.
                3. If the API is blocked, switch Data source to Paste PGN and analyze exported games offline.
                4. Read the coach verdict first, then use the blueprint and opening tabs for detail.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_controls():
    st.sidebar.markdown(f"## {APP_TITLE}")
    st.sidebar.caption("Enter a public Chess.com username, choose the categories you care about, and get a structured coaching report.")

    with st.sidebar.form("profile_form"):
        data_source = st.radio(
            "Data source",
            ["Chess.com API", "Paste PGN"],
            index=0 if st.session_state.get("data_source", "Chess.com API") == "Chess.com API" else 1,
            horizontal=True,
        )
        username = st.text_input(
            "Chess.com username",
            value=st.session_state.get("username_input", ""),
            placeholder="for example: hikaru",
        )
        pgn_text = ""
        if data_source == "Paste PGN":
            pgn_text = st.text_area(
                "Paste PGN games",
                value=st.session_state.get("pgn_text", ""),
                height=170,
                placeholder='Paste one or many games starting with [Event "..."]',
            )
        range_preset = st.selectbox(
            "Quick date range",
            options=DATE_PRESET_OPTIONS,
            index=DATE_PRESET_OPTIONS.index(st.session_state.get("range_preset", "Last 90 days")),
        )
        start_date = st.date_input(
            "From date",
            value=st.session_state.get("start_date", date.today() - timedelta(days=DEFAULT_RANGE_DAYS)),
        )
        end_date = st.date_input(
            "To date",
            value=st.session_state.get("end_date", date.today()),
        )
        max_games = st.slider("Maximum recent games", 30, 250, st.session_state.get("max_games", DEFAULT_MAX_GAMES), step=10)
        rated_only = st.checkbox("Rated games only", value=st.session_state.get("rated_only", True))
        selected_time_classes = st.multiselect(
            "Choose rating categories",
            options=TIME_CLASS_FILTER_OPTIONS,
            default=st.session_state.get("selected_time_classes", DEFAULT_TIME_CLASS_FILTERS),
            format_func=pretty_label,
            max_selections=5,
            help="Pick one or many categories like Blitz, Rapid, Bullet, or Daily. You can choose up to 5.",
        )
        submit_label = "Analyze PGN Games" if data_source == "Paste PGN" else "Analyze Chess.com Profile"
        submit = st.form_submit_button(submit_label, use_container_width=True)

    resolved_range = resolve_date_preset(range_preset)
    if resolved_range:
        start_date, end_date = resolved_range

    st.session_state["range_preset"] = range_preset
    st.session_state["data_source"] = data_source
    st.session_state["pgn_text"] = pgn_text
    st.session_state["start_date"] = start_date
    st.session_state["end_date"] = end_date
    st.session_state["max_games"] = max_games
    st.session_state["rated_only"] = rated_only
    st.session_state["selected_time_classes"] = selected_time_classes

    st.sidebar.markdown("### Current setup")
    st.sidebar.caption(
        f"Source: {data_source} | Range: {format_date_range(start_date, end_date)} | Categories: {selected_class_caption(selected_time_classes or TIME_CLASS_FILTER_OPTIONS)}"
    )

    with st.sidebar.expander("Run guide"):
        st.markdown(
            """
            1. Install Streamlit if needed: `pip install streamlit`
            2. Run: `streamlit run "python project/test.py"`
            3. Paste a Chess.com username
            4. Choose a day range or use a quick preset
            5. Choose one or many categories like Blitz, Rapid, Bullet, or Daily
            6. If Chess.com API is blocked, switch Data source to Paste PGN
            7. Open the Opponent Prep and Position Lab tabs for deeper scouting
            """
        )
    with st.sidebar.expander("How to read the report"):
        st.markdown(
            """
            Start with `Overview` for the verdict and top priorities.
            Open `Coach Blueprint` for a full training and game-day plan.
            Use `Formats & Ratings` and `Openings & Games` for the detailed evidence.
            """
        )
    return username, submit


def main():
    inject_styles()
    ensure_runtime_state()
    username, submit = sidebar_controls()

    if submit:
        st.session_state["username_input"] = username.strip()
        st.session_state["analysis"] = None
        st.session_state["opponent_summary"] = None
        cleaned_username = username.strip()
        if not cleaned_username:
            st.error("Enter a Chess.com username first.")
        elif not st.session_state.get("selected_time_classes"):
            st.error("Choose at least one rating category to analyze.")
        elif st.session_state["start_date"] > st.session_state["end_date"]:
            st.error("The start date must be before the end date.")
        else:
            if st.session_state.get("data_source") == "Paste PGN":
                pgn_text = st.session_state.get("pgn_text", "").strip()
                if not pgn_text:
                    st.error("Paste at least one PGN game first.")
                else:
                    try:
                        with st.spinner("Analyzing pasted PGN games ..."):
                            games = load_games_from_pgn(
                                cleaned_username,
                                pgn_text,
                                st.session_state["selected_time_classes"],
                                st.session_state["start_date"],
                                st.session_state["end_date"],
                                st.session_state["max_games"],
                            )
                        if not games:
                            st.warning("No PGN games matched the selected username, categories, and date range.")
                        else:
                            st.session_state["analysis"] = analyze_games(
                                cleaned_username,
                                offline_profile(cleaned_username),
                                {},
                                games,
                                st.session_state["selected_time_classes"],
                                st.session_state["start_date"],
                                st.session_state["end_date"],
                            )
                    except (RuntimeError, ValueError) as exc:
                        show_runtime_error(exc)
            else:
                try:
                    with st.spinner(f"Analyzing {cleaned_username} on Chess.com ..."):
                        profile, stats, games = fetch_player_bundle(
                            cleaned_username,
                            st.session_state["start_date"],
                            st.session_state["end_date"],
                            st.session_state["max_games"],
                            st.session_state["rated_only"],
                            st.session_state["selected_time_classes"],
                        )
                    if not games:
                        st.warning("No public standard chess games were found in the selected categories and date range.")
                    else:
                        st.session_state["analysis"] = analyze_games(
                            cleaned_username,
                            profile,
                            stats,
                            games,
                            st.session_state["selected_time_classes"],
                            st.session_state["start_date"],
                            st.session_state["end_date"],
                        )
                except RuntimeError as exc:
                    show_runtime_error(exc)
                    st.info("If DNS keeps failing, change Data source to Paste PGN and analyze exported Chess.com games without internet access.")

    summary = st.session_state.get("analysis")
    if summary is not None and not analysis_is_compatible(summary):
        st.session_state["analysis"] = None
        st.session_state["opponent_summary"] = None
        summary = None
        st.warning("The saved analysis was from an older app version, so it was cleared. Run the profile again.")
    if not summary:
        render_empty_state()
        return

    render_top_dashboard(summary)

    overview_tab, blueprint_tab, formats_tab, profile_tab, opponent_tab, position_tab = st.tabs(
        ["Overview", "Coach Blueprint", "Formats & Ratings", "Openings & Games", "Opponent Prep", "Position Lab"]
    )
    with overview_tab:
        render_overview_tab(summary)
    with blueprint_tab:
        render_blueprint_tab(summary)
    with formats_tab:
        render_formats_tab(summary)
    with profile_tab:
        render_profile_tab(summary)
    with opponent_tab:
        render_opponent_tab(summary)
    with position_tab:
        render_position_tab()

    st.caption(
        "This report is based on public game archives and heuristic coaching logic. For full move-by-move engine review, attach a local engine later."
    )


if __name__ == "__main__":
    main()
