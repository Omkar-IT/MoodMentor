from welcome_image import WELCOME_IMAGE_B64
import os, re, random, calendar
from datetime import date, datetime
import requests, streamlit as st
import matplotlib.pyplot as plt
from db import (init_db, save_mood_log, save_manual_mood, MOOD_LABELS,
                 get_mood_logs_for_month, get_user_mood_history,
                 get_all_employee_mood_logs, get_latest_mood_per_employee,
                 save_daily_wellness, get_daily_wellness_range)
from auth import (make_token, read_token, get_user, username_taken, create_user,
                   verify_user, set_password, check_pw, new_otp, save_otp, check_otp)
from email_utils import send_otp
from weekly_report import (DEFAULT_WEEKLY_WEIGHTS, build_weekly_report_data, aggregate_week,
                           generate_weekly_summary, recommendations, achievements, build_weekly_pdf)

st.set_page_config(page_title="MoodMentor", page_icon="🧠", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ---- Vivid multi-hue palette ----
BRAND_GREEN = "#9F7AEA"        # primary purple (var name kept for compatibility)
BRAND_GREEN_DARK = "#805AD5"
PRIMARY = BRAND_GREEN
PRIMARY_DARK = BRAND_GREEN_DARK
PINK = "#EC4899"
CYAN = "#06B6D4"
GREEN = "#10B981"
AMBER = "#F59E0B"
CORAL = "#F97066"
TITLE_COLOR = "#6B21A8"
INK = "#1E1B2E"
MUTED = "#6B7280"
GLASS_BG = "rgba(255, 255, 255, 0.62)"
GLASS_BORDER = "rgba(255, 255, 255, 0.9)"
BTN_GRADIENT = "linear-gradient(135deg, #EC4899 0%, #9F7AEA 50%, #6366F1 100%)"
BTN_HOVER = "linear-gradient(135deg, #DB2777 0%, #805AD5 50%, #4F46E5 100%)"

QUOTES = [
    "Small steps lead to big changes.",
    "Every day is a fresh start.",
    "Breathe in peace, exhale stress.",
    "You are doing better than you think.",
    "Your mental health is a priority.",
]

MOOD_STYLE = {
    "Amazing": {"emoji": "🤩", "color": "#10B981", "bg": "#D1FAE5", "border": "#10B981", "glow": "rgba(16,185,129,0.45)"},
    "Happy":   {"emoji": "😀", "color": "#EC4899", "bg": "#FCE7F3", "border": "#EC4899", "glow": "rgba(236,72,153,0.45)"},
    "Normal":  {"emoji": "😐", "color": "#06B6D4", "bg": "#CFFAFE", "border": "#06B6D4", "glow": "rgba(6,182,212,0.45)"},
    "Sad":     {"emoji": "🙁", "color": "#F59E0B", "bg": "#FEF3C7", "border": "#F59E0B", "glow": "rgba(245,158,11,0.45)"},
    "Angry":   {"emoji": "🤬", "color": "#EF4444", "bg": "#FEE2E2", "border": "#EF4444", "glow": "rgba(239,68,68,0.45)"},
}
def style_for(label):
    return MOOD_STYLE.get(label, {"emoji": "⬜", "color": "#bdbdbd", "bg": "#F7FAFC", "border": "#F7FAFC", "glow": "transparent"})

MOOD_TO_NUM = {"Amazing": 2, "Happy": 1, "Normal": 0, "Sad": -1, "Angry": -2}

def inject_css():
    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {{ font-family: 'Poppins', sans-serif; }}

        @media (prefers-reduced-motion: reduce) {{
            * {{ animation: none !important; transition: none !important; }}
        }}

        /* ---- Animated moving-gradient app background ---- */
        .stApp {{
            background:
                radial-gradient(900px 500px at 5% 0%, rgba(236,72,153,0.20), transparent 55%),
                radial-gradient(900px 500px at 95% 10%, rgba(99,102,241,0.22), transparent 55%),
                radial-gradient(800px 500px at 50% 100%, rgba(6,182,212,0.18), transparent 55%),
                linear-gradient(160deg, #FDF4FF 0%, #F0F4FF 45%, #ECFEFF 100%);
            background-size: 140% 140%, 140% 140%, 140% 140%, 200% 200%;
            animation: bgFloat 16s ease-in-out infinite alternate;
        }}
        @keyframes bgFloat {{
            0%   {{ background-position: 0% 0%, 100% 0%, 50% 100%, 0% 0%; }}
            100% {{ background-position: 10% 10%, 90% 15%, 55% 90%, 100% 100%; }}
        }}
        #MainMenu, footer {{visibility: hidden;}}

        ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(180deg, {PINK}, {PRIMARY}, {CYAN});
            border-radius: 10px;
        }}

        /* ---- Floating decorative blobs (behind glass panels) ---- */
        @keyframes blobFloat {{
            0%   {{ transform: translate(0,0) scale(1) rotate(0deg); }}
            33%  {{ transform: translate(20px,-25px) scale(1.08) rotate(8deg); }}
            66%  {{ transform: translate(-15px,15px) scale(0.95) rotate(-6deg); }}
            100% {{ transform: translate(0,0) scale(1) rotate(0deg); }}
        }}

        /* ---- Sparkle particles ---- */
        @keyframes sparkleFloat {{
            0%   {{ transform: translateY(0) scale(0.8); opacity: 0.2; }}
            50%  {{ transform: translateY(-18px) scale(1.15); opacity: 1; }}
            100% {{ transform: translateY(0) scale(0.8); opacity: 0.2; }}
        }}
        .sparkle {{
            position: absolute; font-size: 1.1rem; pointer-events: none;
            animation: sparkleFloat 3.5s ease-in-out infinite;
            filter: drop-shadow(0 0 6px rgba(236,72,153,0.6));
        }}

        /* ---- Pop-in / staggered entrance ---- */
        @keyframes popIn {{
            0%   {{ opacity: 0; transform: translateY(16px) scale(0.94); }}
            60%  {{ opacity: 1; transform: translateY(-3px) scale(1.015); }}
            100% {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ---- Pulsing glow ring ---- */
        @keyframes glowPulse {{
            0%, 100% {{ box-shadow: 0 22px 50px -18px rgba(99, 102, 241, 0.28); }}
            50%      {{ box-shadow: 0 26px 60px -16px rgba(236, 72, 153, 0.4); }}
        }}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(255,255,255,0.85) 0%, rgba(253,244,255,0.85) 100%);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-right: 1px solid {GLASS_BORDER};
        }}
        section[data-testid="stSidebar"] .stRadio > label {{ font-weight: 700; color: {INK}; }}
        section[data-testid="stSidebar"] div[role="radiogroup"] label {{
            padding: 11px 15px; border-radius: 14px; margin-bottom: 5px;
            transition: all 200ms ease-out;
        }}
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
            background: linear-gradient(90deg, rgba(236,72,153,0.16), rgba(99,102,241,0.16));
            transform: translateX(5px) scale(1.02);
        }}

        /* ---- Translucent chart box (sits behind charts) ---- */
        .chart-box {{
            background: rgba(255,255,255,0.55);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border-radius: 20px;
            padding: 18px 20px 4px 20px;
            border: 1px solid rgba(255,255,255,0.85);
            box-shadow: 0 14px 30px -12px rgba(99,102,241,0.2);
            margin-bottom: 20px;
        }}

        /* ---- Glow-ring gradient border card, pulsing + pop-in ---- */
        .mm-card {{
            position: relative;
            background: {GLASS_BG};
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 26px; padding: 28px 30px;
            border: 1.5px solid transparent;
            background-clip: padding-box;
            margin-bottom: 22px;
            animation: popIn 550ms cubic-bezier(0.22,1,0.36,1), glowPulse 5s ease-in-out infinite 600ms;
        }}
        .mm-card::before {{
            content: ""; position: absolute; inset: -1.5px; border-radius: 27px; z-index: -1;
            background: linear-gradient(135deg, rgba(236,72,153,0.55), rgba(99,102,241,0.55), rgba(6,182,212,0.55));
            opacity: 0.6;
            background-size: 200% 200%;
            animation: gradientShift 6s ease infinite;
        }}
        @keyframes gradientShift {{
            0%   {{ background-position: 0% 50%; }}
            50%  {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        .mm-card h4, .mm-card h3 {{ margin-top: 0; color: {TITLE_COLOR}; font-weight: 700; }}

        /* ---- Metric tiles: staggered bounce-in + hover lift ---- */
        .mm-metric {{
            background: {GLASS_BG};
            backdrop-filter: blur(20px);
            border-radius: 22px; padding: 22px 18px;
            border: 1px solid {GLASS_BORDER}; text-align: center;
            box-shadow: 0 16px 34px -12px rgba(99, 102, 241, 0.22);
            transition: transform 220ms ease-out, box-shadow 220ms ease-out;
            animation: popIn 550ms cubic-bezier(0.22,1,0.36,1) both;
        }}
        .mm-metric:hover {{
            transform: translateY(-6px) scale(1.04) rotate(-1deg);
            box-shadow: 0 24px 44px -12px rgba(236, 72, 153, 0.4);
        }}
        .mm-metric .mm-label {{ color: {MUTED}; font-size: 11.5px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }}
        .mm-metric .mm-value {{
            font-size: 30px; font-weight: 800; margin-top: 6px;
            background: linear-gradient(135deg, {PINK}, {PRIMARY}, {CYAN});
            background-size: 200% auto;
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            animation: gradientShift 4s ease infinite;
        }}
        .mm-metric .mm-sub {{ font-size: 12px; color: {GREEN}; font-weight: 700; margin-top: 4px; }}

        /* ---- Badges — subtle pulse ---- */
        .mm-badge-positive {{
            display:inline-block; background: linear-gradient(135deg, {GREEN}, #059669);
            color: white; padding:5px 14px; border-radius:20px; font-size:12.5px; font-weight:800;
            box-shadow: 0 6px 14px -4px rgba(16,185,129,0.5);
            animation: badgePulse 2.2s ease-in-out infinite;
        }}
        @keyframes badgePulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.06); }}
        }}

        /* ---- Header — animated moving gradient text ---- */
        .mm-header {{ display:flex; justify-content:space-between; align-items:center; padding-bottom: 10px; margin-bottom: 14px; }}
        .mm-header h2 {{
            margin: 0; font-weight: 800;
            background: linear-gradient(135deg, {PINK} 0%, {PRIMARY} 50%, {CYAN} 100%);
            background-size: 200% auto;
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            animation: gradientShift 5s ease infinite;
        }}
        .mm-header p {{ margin: 3px 0 0 0; color:{MUTED}; font-size: 14px; font-weight: 500; }}

        /* ---- Buttons — gradient shift + shine sweep + bold hover ---- */
        div.stButton > button,
        .stFormSubmitButton > button,
        button[kind="primary"],
        button[kind="secondary"],
        div[data-testid="stButton"] button,
        div[data-testid="stFormSubmitButton"] button {{
            position: relative; overflow: hidden;
            border-radius: 16px !important;
            font-weight: 700 !important;
            border: none !important;
            transition: transform 200ms ease-out, box-shadow 200ms ease-out, background 200ms ease-out !important;
        }}
        div.stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"],
        button[kind="primary"],
        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button[kind="primary"] {{
            background: {BTN_GRADIENT} !important;
            background-size: 200% 200% !important;
            color: white !important;
            box-shadow: 0 14px 28px -10px rgba(236, 72, 153, 0.5) !important;
            animation: gradientShift 3s ease infinite !important;
        }}
        div.stButton > button[kind="primary"]::after,
        .stFormSubmitButton > button[kind="primary"]::after,
        button[kind="primary"]::after {{
            content: ""; position: absolute; top: 0; left: -60%; width: 40%; height: 100%;
            background: linear-gradient(120deg, transparent, rgba(255,255,255,0.5), transparent);
            transform: skewX(-20deg);
            animation: shineSweep 2.8s ease-in-out infinite;
        }}
        @keyframes shineSweep {{
            0%   {{ left: -60%; }}
            50%  {{ left: 120%; }}
            100% {{ left: 120%; }}
        }}
        div.stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover,
        button[kind="primary"]:hover,
        div[data-testid="stButton"] button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {{
            background: {BTN_HOVER} !important;
            transform: translateY(-4px) scale(1.025);
            box-shadow: 0 22px 40px -10px rgba(99, 102, 241, 0.6) !important;
        }}
        div.stButton > button:not([kind="primary"]),
        div[data-testid="stButton"] button:not([kind="primary"]) {{
            background: linear-gradient(135deg, rgba(236,72,153,0.10), rgba(99,102,241,0.10)) !important;
            color: {TITLE_COLOR} !important;
            border: 1.5px solid rgba(99,102,241,0.18) !important;
        }}
        div.stButton > button:not([kind="primary"]):hover,
        div[data-testid="stButton"] button:not([kind="primary"]):hover {{
            background: linear-gradient(135deg, rgba(236,72,153,0.22), rgba(99,102,241,0.22)) !important;
            transform: translateY(-3px) scale(1.02);
        }}

        /* ---- Text inputs ---- */
        .stTextInput > div > div > input,
        div[data-testid="stTextInput"] input,
        .stTextArea textarea,
        div[data-testid="stTextArea"] textarea {{
            border-radius: 16px !important;
            border: 1.5px solid rgba(99,102,241,0.2) !important;
            background: rgba(255,255,255,0.85) !important;
            transition: border-color 200ms ease-out, box-shadow 200ms ease-out, transform 150ms ease-out !important;
        }}
        .stTextInput > div > div > input:focus,
        .stTextArea textarea:focus {{
            border-color: {PINK} !important;
            box-shadow: 0 0 0 5px rgba(236, 72, 153, 0.22) !important;
            transform: scale(1.005);
        }}

        /* ---- Journal: warm coral/amber, pulsing ---- */
        .journal-card {{
            position: relative;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 26px; padding: 30px 32px;
            box-shadow: 0 20px 44px -16px rgba(249, 112, 102, 0.3);
            margin-bottom: 22px;
            border: 1.5px solid rgba(255,255,255,0.9);
            animation: popIn 550ms cubic-bezier(0.22,1,0.36,1);
        }}
        .journal-header {{ text-align: center; padding: 8px 0 22px 0; }}
        .journal-header .j-emoji {{ font-size: 2.6rem; line-height: 1; display:inline-block; animation: wiggle 2.4s ease-in-out infinite; }}
        @keyframes wiggle {{
            0%, 100% {{ transform: rotate(0deg); }}
            25%  {{ transform: rotate(-8deg) scale(1.05); }}
            75%  {{ transform: rotate(8deg) scale(1.05); }}
        }}
        .journal-header .j-title {{
            font-size: 1.25rem; font-weight: 800; margin-top: 8px;
            background: linear-gradient(135deg, {AMBER}, {CORAL});
            background-size: 200% auto;
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            animation: gradientShift 4s ease infinite;
        }}
        .journal-card div.stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, {AMBER} 0%, {CORAL} 100%) !important;
            background-size: 200% 200% !important;
            box-shadow: 0 14px 28px -10px rgba(249, 112, 102, 0.5) !important;
        }}
        .journal-card div.stButton > button[kind="primary"]:hover {{
            background: linear-gradient(135deg, {CORAL} 0%, #DC2626 100%) !important;
        }}
        .journal-card .stTextArea textarea {{
            border-radius: 18px !important;
            background: rgba(255,251,240,0.85) !important;
            border: 1.5px solid rgba(245,158,11,0.22) !important;
        }}
        .journal-card .streamlit-expanderHeader {{
            border-radius: 15px !important;
            background: rgba(255,247,230,0.7) !important;
        }}

        /* ---- Calendar: cyan/teal, glowing pulsing today, staggered day pop ---- */
        .calendar-card {{
            background: rgba(255,255,255,0.87);
            border-radius: 26px; padding: 0;
            box-shadow: 0 20px 44px -16px rgba(6, 182, 212, 0.3);
            margin-bottom: 22px; overflow: hidden;
            animation: popIn 550ms cubic-bezier(0.22,1,0.36,1);
        }}
        .calendar-header-bar {{
            background: linear-gradient(135deg, {CYAN} 0%, {PRIMARY} 100%);
            background-size: 200% 200%;
            animation: gradientShift 5s ease infinite;
            padding: 20px 28px; display: flex; justify-content: space-between; align-items: center;
        }}
        .calendar-header-bar .cal-title {{ font-size: 1.3rem; font-weight: 800; color: white; }}
        .calendar-body {{ padding: 22px 28px; }}
        .weekday-pill {{
            background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(99,102,241,0.15));
            color: {TITLE_COLOR};
            aspect-ratio: 1; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 0.85rem; margin: 0 auto; width: 34px; height: 34px;
        }}
        .day-pill {{
            aspect-ratio: 1; border-radius: 14px;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            border: 1.5px solid rgba(99,102,241,0.08);
            transition: transform 180ms ease-out, box-shadow 180ms ease-out;
            padding: 6px 2px;
            animation: popIn 450ms cubic-bezier(0.22,1,0.36,1) both;
        }}
        .day-pill:hover {{ transform: scale(1.15) rotate(-2deg); box-shadow: 0 10px 22px -6px rgba(99,102,241,0.45); z-index: 2; }}
        .day-pill.today {{
            border-color: {PINK}; font-weight: 800; color: {PINK}; border-width: 2.5px;
            animation: todayPulse 2s ease-in-out infinite, popIn 450ms cubic-bezier(0.22,1,0.36,1) both;
        }}
        @keyframes todayPulse {{
            0%, 100% {{ box-shadow: 0 0 0 3px rgba(236,72,153,0.18); }}
            50%      {{ box-shadow: 0 0 0 7px rgba(236,72,153,0.28); }}
        }}
        .day-num {{ font-size: 11px; font-weight: 700; }}
        .calendar-legend-bar {{
            background: linear-gradient(135deg, rgba(255,251,235,0.9), rgba(207,250,254,0.9));
            padding: 18px 28px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px;
            font-size: 0.8rem; font-weight: 700; color: {INK};
        }}

        /* ---- Login page — glowing, sparkling, floating blobs ---- */
        .login-shell {{
            position: relative; overflow: visible;
            background: {GLASS_BG};
            backdrop-filter: blur(24px);
            border-radius: 32px;
            box-shadow: 0 30px 60px -18px rgba(99,102,241,0.3);
            border: 1.5px solid {GLASS_BORDER};
            animation: popIn 650ms cubic-bezier(0.22,1,0.36,1), glowPulse 5s ease-in-out infinite 700ms;
        }}
        .login-blob-1, .login-blob-2 {{
            position: absolute; border-radius: 50%; filter: blur(50px); z-index: -1; pointer-events:none;
        }}
        .login-blob-1 {{
            width: 220px; height: 220px; background: radial-gradient(circle, rgba(236,72,153,0.35), transparent 70%);
            top: -60px; left: -60px; animation: blobFloat 9s ease-in-out infinite;
        }}
        .login-blob-2 {{
            width: 260px; height: 260px; background: radial-gradient(circle, rgba(6,182,212,0.3), transparent 70%);
            bottom: -80px; right: -60px; animation: blobFloat 11s ease-in-out infinite reverse;
        }}
        .brand-row {{
            font-size: 1.7rem; font-weight: 900;
            background: linear-gradient(135deg, {PINK}, {PRIMARY}, {CYAN});
            background-size: 200% auto;
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            display:flex; align-items:center; gap:8px; margin-bottom: 4px;
            animation: gradientShift 4s ease infinite;
        }}
        .quote-box {{
            background: linear-gradient(90deg, rgba(236,72,153,0.08), rgba(99,102,241,0.08));
            border-left: 4px solid {PINK};
            padding: 14px 18px; border-radius: 0 14px 14px 0;
            font-style: italic; font-weight: 600; color: {INK}; margin: 18px 0 24px 0;
        }}
        .greet-title {{
            font-size: 1.7rem; font-weight: 800; margin-bottom: 3px;
            background: linear-gradient(135deg, {INK}, {PRIMARY}, {PINK});
            background-size: 200% auto;
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            animation: gradientShift 5s ease infinite;
        }}
        .greet-sub {{ color: {MUTED}; font-size: 0.98rem; margin-bottom: 22px; font-weight: 500; }}
        .divider-text {{
            text-align:center; color:{MUTED}; font-size:0.85rem; margin: 20px 0;
            display:flex; align-items:center; gap:12px; font-weight: 600;
        }}
        .divider-text::before, .divider-text::after {{
            content:''; flex:1; border-bottom:1.5px solid rgba(99,102,241,0.15);
        }}
        .stars-twinkle {{ display:inline-block; animation: twinkle 1.6s ease-in-out infinite; }}
        @keyframes twinkle {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50%      {{ opacity: 0.55; transform: scale(0.92); }}
        }}

        /* ---- Hero mood-face panel ---- */
        @keyframes heroBgShift {{
            0%   {{ background-position: 0% 50%; }}
            50%  {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        @keyframes floatSlow {{
            0%, 100% {{ transform: translateY(0) rotate(0deg); }}
            50%      {{ transform: translateY(-12px) rotate(1.5deg); }}
        }}
        @keyframes blinkEyes {{
            0%, 92%, 100% {{ transform: scaleY(1); }}
            96%           {{ transform: scaleY(0.15); }}
        }}
        @keyframes orbit {{
            0%   {{ transform: rotate(0deg) translateX(128px) rotate(0deg); }}
            100% {{ transform: rotate(360deg) translateX(128px) rotate(-360deg); }}
        }}
        @keyframes bobChip {{
            0%, 100% {{ transform: translateY(0) scale(1); }}
            50%      {{ transform: translateY(-8px) scale(1.06); }}
        }}
        @keyframes ringPulse {{
            0%, 100% {{ opacity: 0.55; transform: translate(-50%,-50%) scale(1); }}
            50%      {{ opacity: 0.15; transform: translate(-50%,-50%) scale(1.14); }}
        }}
        @keyframes ringPulseSlow {{
            0%, 100% {{ opacity: 0.35; transform: translate(-50%,-50%) scale(1); }}
            50%      {{ opacity: 0.08; transform: translate(-50%,-50%) scale(1.08); }}
        }}
        @keyframes heroGlow {{
            0%, 100% {{ box-shadow: 0 40px 90px -20px rgba(147,51,234,0.5), inset 0 -16px 30px rgba(0,0,0,0.08), 0 0 0 0 rgba(236,72,153,0.0); }}
            50%      {{ box-shadow: 0 46px 100px -18px rgba(236,72,153,0.62), inset 0 -16px 30px rgba(0,0,0,0.08), 0 0 60px 4px rgba(236,72,153,0.18); }}
        }}
        .hero-badge {{
            display:inline-flex; align-items:center; gap:6px;
            background: rgba(255,255,255,0.7); backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.9);
            padding: 6px 14px; border-radius: 999px; font-size: 0.72rem; font-weight: 800;
            color: {TITLE_COLOR}; letter-spacing: 0.03em; text-transform: uppercase;
            box-shadow: 0 8px 20px -8px rgba(99,102,241,0.35);
            animation: popIn 600ms cubic-bezier(0.22,1,0.36,1) 150ms both;
        }}
    </style>
    """, unsafe_allow_html=True)

def donut_chart(counts: dict, size=2.6):
    """Small donut chart themed to the mood/emotion colors — used for
    'Top Emotions' / 'Emotion Distribution' style widgets."""
    labels, values, colors = [], [], []
    for k, v in counts.items():
        if v > 0:
            labels.append(k); values.append(v)
            colors.append(style_for(k)["color"])
    if not values:
        return None
    fig, ax = plt.subplots(figsize=(size, size))
    ax.pie(
        values, colors=colors, startangle=90,
        wedgeprops=dict(width=0.38, edgecolor="white"),
        autopct="%1.0f%%", pctdistance=0.82,
        textprops=dict(color="white", fontsize=9, fontweight="bold"),
    )
    ax.set(aspect="equal")
    fig.patch.set_alpha(0.0)
    return fig

def metric_tile(label, value, sub=None, delay=0):
    sub_html = f"<div class='mm-sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"<div class='mm-metric' style='animation-delay:{delay}ms'><div class='mm-label'>{label}</div>"
        f"<div class='mm-value'>{value}</div>{sub_html}</div>",
        unsafe_allow_html=True,
    )

inject_css()

@st.cache_resource
def setup(): init_db()
setup()

if "page" not in st.session_state: st.session_state.page = "welcome"
if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"
if "token" not in st.session_state: st.session_state.token = None
if "email" not in st.session_state: st.session_state.email = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "cal_year" not in st.session_state: st.session_state.cal_year = date.today().year
if "cal_month" not in st.session_state: st.session_state.cal_month = date.today().month
if "today_mood_saved" not in st.session_state: st.session_state.today_mood_saved = False
if "nav" not in st.session_state: st.session_state.nav = "Home"

def goto_auth(mode): st.session_state.auth_mode = mode; st.rerun()

def valid_pw(pw):
    return len(pw) >= 8 and re.search(r"[A-Za-z]", pw) and re.search(r"[0-9]", pw)


if st.session_state.token:
    user = read_token(st.session_state.token)

    if user:
        role = user.get("role", "employee")
        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        with st.sidebar:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;padding:6px 4px 18px 4px'>"
                f"<span style='font-size:22px'>🧠</span>"
                f"<span style='font-size:18px;font-weight:800;color:{INK}'>Mood<span style='color:{BRAND_GREEN}'>Mentor</span></span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            if role == "employee":
                nav_options = [
                    "Home",
                    "Analyze Text",
                    "Journal",
                    "Wellness Chat",
                    "Face Recognition",
                    "Dashboard",
                    "Weekly Report"
                ]
            else:
                nav_options = ["Reports"]

            st.session_state.nav = st.radio(
                "Navigate",
                nav_options,
                index=nav_options.index(st.session_state.nav)
                if st.session_state.nav in nav_options else 0,
                label_visibility="collapsed",
            )

            st.divider()
            st.caption(f"Signed in as **{user['username']}**")
            st.caption(f"{user['email']} · {role.capitalize()}")

            if st.button("Log out", use_container_width=True):
                st.session_state.token = None
                st.session_state.page = "welcome"
                st.rerun()

        greeting = (
            "Good Morning"
            if datetime.now().hour < 12
            else (
                "Good Afternoon"
                if datetime.now().hour < 18
                else "Good Evening"
            )
        )

        st.markdown(
            f"<div class='mm-header'><div><h2>{greeting}, {user['username']}! 👋</h2>"
            f"<p>Here's your emotional wellness overview.</p></div></div>",
            unsafe_allow_html=True,
        )

        if role == "employee":
            section = st.session_state.nav

            if section == "Home":
                history_all = get_user_mood_history(user["id"], limit=500)
                latest = history_all[0] if history_all else None
                today_count = sum(
                    1 for h in history_all
                    if h["mood_date"] == date.today()
                )

                streak = 0
                day_ptr = date.today()
                day_set = {h["mood_date"] for h in history_all}

                while day_ptr in day_set:
                    streak += 1
                    day_ptr = date.fromordinal(
                        day_ptr.toordinal() - 1
                    )

                positive_count = sum(
                    1 for h in history_all
                    if h["sentiment"] in ("Amazing", "Happy")
                )

                overall_score = (
                    int(100 * positive_count / len(history_all))
                    if history_all else 0
                )

                m1, m2, m3, m4 = st.columns(4)

                with m1:
                    if latest:
                        s = style_for(latest["sentiment"])
                        metric_tile(
                            "Current Mood",
                            f"{s['emoji']} {latest['sentiment']}",
                            delay=0
                        )
                    else:
                        metric_tile(
                            "Current Mood",
                            "—",
                            delay=0
                        )

                with m2:
                    metric_tile(
                        "Overall Score",
                        f"{overall_score}%",
                        "Positive" if overall_score >= 50 else "Needs care",
                        delay=80
                    )

                with m3:
                    metric_tile(
                        "Entries Today",
                        today_count,
                        delay=160
                    )

                with m4:
                    metric_tile(
                        "Current Streak",
                        f"{streak} Days",
                        delay=240
                    )

                st.write("")

                st.markdown(
                    "<div class='mm-card'><h3>How Do You Feel?</h3></div>",
                    unsafe_allow_html=True
                )

                now = datetime.now()

                st.caption(
                    f"📅 {now.strftime('%Y-%m-%d')}  "
                    f"🕒 {now.strftime('%H:%M')}"
                )

                cols = st.columns(len(MOOD_LABELS))
                picked = st.session_state.get("picked_mood")

                for col, label in zip(cols, MOOD_LABELS):
                    s = style_for(label)

                    with col:
                        st.markdown(
                            f"<div style='text-align:center;font-size:40px;"
                            f"filter:drop-shadow(0 6px 10px {s['glow']});"
                            f"animation:wiggle 3s ease-in-out infinite;"
                            f"display:block'>{s['emoji']}</div>"
                            f"<div style='text-align:center;"
                            f"color:{s['color']};font-weight:700'>{label}</div>",
                            unsafe_allow_html=True,
                        )

                        if st.button(
                            "Select",
                            key=f"pick_{label}",
                            use_container_width=True
                        ):
                            st.session_state.picked_mood = label

                st.write("")

                confirm_col = st.columns([3, 1, 3])[1]

                with confirm_col:
                    disabled = picked is None

                    if st.button(
                        "Save mood",
                        type="primary",
                        disabled=disabled,
                        use_container_width=True
                    ):
                        save_manual_mood(
                            user["id"],
                            st.session_state.picked_mood
                        )

                        st.session_state.today_mood_saved = True
                        st.session_state.picked_mood = None
                        st.rerun()

                if st.session_state.today_mood_saved:
                    st.success("Today's mood saved!")
                    st.session_state.today_mood_saved = False

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

                # ---- Calendar ----

                st.markdown(
                    '<div class="calendar-card">',
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="calendar-header-bar">',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f'<div class="cal-title">'
                    f'{calendar.month_name[st.session_state.cal_month]} '
                    f'{st.session_state.cal_year}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="calendar-body">',
                    unsafe_allow_html=True
                )

                nav_l, nav_mid, nav_r = st.columns([1, 4, 1])

                if nav_l.button("‹ Prev"):
                    m = st.session_state.cal_month - 1
                    y = st.session_state.cal_year

                    if m == 0:
                        m, y = 12, y - 1

                    st.session_state.cal_month = m
                    st.session_state.cal_year = y
                    st.rerun()

                if nav_r.button("Next ›"):
                    m = st.session_state.cal_month + 1
                    y = st.session_state.cal_year

                    if m == 13:
                        m, y = 1, y + 1

                    st.session_state.cal_month = m
                    st.session_state.cal_year = y
                    st.rerun()

                logs = get_mood_logs_for_month(
                    user["id"],
                    st.session_state.cal_year,
                    st.session_state.cal_month
                )

                by_day = {
                    row["mood_date"].day: row
                    for row in logs
                }

                weeks = calendar.Calendar(
                    firstweekday=6
                ).monthdayscalendar(
                    st.session_state.cal_year,
                    st.session_state.cal_month
                )

                day_names = [
                    "Su", "Mo", "Tu", "We",
                    "Th", "Fr", "Sa"
                ]

                header_cols = st.columns(7)

                for c, name in zip(header_cols, day_names):
                    c.markdown(
                        f"<div class='weekday-pill'>{name}</div>",
                        unsafe_allow_html=True
                    )

                today = date.today()
                day_counter = 0

                for week in weeks:
                    cols = st.columns(7)

                    for col, day_num in zip(cols, week):

                        if day_num == 0:
                            col.write("")
                            continue

                        entry = by_day.get(day_num)

                        s = style_for(
                            entry["sentiment"] if entry else None
                        )

                        is_today = (
                            day_num == today.day
                            and st.session_state.cal_month == today.month
                            and st.session_state.cal_year == today.year
                        )

                        today_class = " today" if is_today else ""

                        border_style = (
                            f"border-color:{s['border']};"
                            if entry and not is_today
                            else ""
                        )

                        bg_style = (
                            f"background:{s['bg']};"
                            if entry
                            else "background:#FFFFFF;"
                        )

                        emoji_html = (
                            f"<div style='font-size:1.1rem;"
                            f"line-height:1'>{s['emoji']}</div>"
                            if entry
                            else ""
                        )

                        delay_ms = (day_counter % 14) * 25
                        day_counter += 1

                        col.markdown(
                            f"<div class='day-pill{today_class}' "
                            f"style='{bg_style}{border_style}"
                            f"animation-delay:{delay_ms}ms'>"
                            f"<div class='day-num'>{day_num}</div>"
                            f"{emoji_html}</div>",
                            unsafe_allow_html=True,
                        )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )

                legend_html = "".join(
                    f"<span>{style_for(l)['emoji']} {l}</span>"
                    for l in MOOD_LABELS
                )

                st.markdown(
                    f'<div class="calendar-legend-bar">'
                    f'{legend_html}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )

                # ---- Daily Wellness Details ----

                st.markdown(
                    "<div class='mm-card'><h3>🌿 Daily Wellness Details</h3></div>",
                    unsafe_allow_html=True
                )

                st.caption(
                    "Store stress, sleep and workload separately "
                    "from journal entries. Missing values remain unavailable."
                )

                wc1, wc2, wc3 = st.columns(3)

                with wc1:
                    stress_value = st.number_input(
                        "Stress level (0–10)",
                        min_value=0.0,
                        max_value=10.0,
                        value=5.0,
                        step=0.5,
                        key="daily_stress"
                    )

                with wc2:
                    sleep_value = st.number_input(
                        "Sleep hours",
                        min_value=0.0,
                        max_value=24.0,
                        value=7.0,
                        step=0.5,
                        key="daily_sleep"
                    )

                with wc3:
                    workload_value = st.selectbox(
                        "Workload",
                        ["Not recorded", "Low", "Medium", "High"],
                        key="daily_workload"
                    )

                missing_stress = st.checkbox(
                    "Stress not recorded",
                    key="missing_stress"
                )

                missing_sleep = st.checkbox(
                    "Sleep not recorded",
                    key="missing_sleep"
                )

                missing_workload = st.checkbox(
                    "Workload not recorded",
                    key="missing_workload"
                )

                if st.button(
                    "Save today's wellness details",
                    type="primary",
                    use_container_width=True
                ):
                    save_daily_wellness(
                        user["id"],
                        date.today(),
                        stress_level=None
                        if missing_stress
                        else stress_value,
                        sleep_hours=None
                        if missing_sleep
                        else sleep_value,
                        workload=None
                        if missing_workload
                        or workload_value == "Not recorded"
                        else workload_value,
                    )

                    st.success(
                        "Today's wellness details saved. "
                        "No journal entry was created."
                    )

                    st.rerun()

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

            elif section == "Analyze Text":

                st.markdown(
                    "<div class='mm-card'><h3>📝 Analyze Text</h3></div>",
                    unsafe_allow_html=True
                )

                st.caption(
                    "Enter your text below and let AI analyze your emotions."
                )

                text_in = st.text_area(
                    "Type or paste your text here…",
                    height=160,
                    label_visibility="collapsed",
                    placeholder="Type or paste your text here…"
                )

                st.caption(
                    f"{len(text_in)}/5000 characters"
                )

                if st.button(
                    "Analyze Now",
                    type="primary",
                    use_container_width=True
                ):

                    if not text_in.strip():
                        st.warning("Write something first.")

                    else:

                        with st.spinner("Running NLP analysis…"):

                            try:
                                resp = requests.post(
                                    f"{BACKEND_URL}/analyze-text",
                                    json={"text": text_in},
                                    headers=headers,
                                    timeout=120,
                                )

                            except requests.exceptions.RequestException as e:
                                st.error(
                                    f"Could not reach backend: {e}"
                                )
                                resp = None

                        if resp is not None:

                            if resp.status_code != 200:
                                st.error("Analysis failed.")

                            else:

                                r = resp.json()

                                confidence = r.get(
                                    "emotion_confidence"
                                )

                                save_mood_log(
                                    user["id"],
                                    r["final_sentiment"],
                                    r["final_emotion"],
                                    r["sentiment_scores"]["compound"],
                                    text_in,
                                    confidence=confidence,
                                    positive_score=r["sentiment_scores"].get("pos"),
                                    negative_score=r["sentiment_scores"].get("neg"),
                                    neutral_score=r["sentiment_scores"].get("neu"),
                                    detected_language=r.get("detected_language"),
                                    cleaned_text=r.get("cleaned_text"),
                                )

                                st.subheader("Analysis Results")

                                rc1, rc2 = st.columns(2)

                                with rc1:
                                    st.write("**Overall Emotion**")

                                    s = style_for(
                                        r["final_sentiment"]
                                    )

                                    conf_label = (
                                        f"Confidence: {confidence:.0%}"
                                        if confidence is not None
                                        else ""
                                    )

                                    st.markdown(
                                        f"### {s['emoji']} "
                                        f"{r['final_emotion']}"
                                        + (
                                            f"&nbsp;&nbsp;"
                                            f"<span style='font-size:14px;"
                                            f"color:#6b7280;"
                                            f"font-weight:600'>"
                                            f"{conf_label}</span>"
                                            if conf_label
                                            else ""
                                        ),
                                        unsafe_allow_html=True,
                                    )

                                    badge = "mm-badge-positive"

                                    st.markdown(
                                        f"<span class='{badge}'>"
                                        f"{r['final_sentiment']}</span>"
                                        f"&nbsp;&nbsp;Score: "
                                        f"**{r['sentiment_scores']['compound']:.2f}**",
                                        unsafe_allow_html=True,
                                    )

                                with rc2:
                                    st.markdown(
                                        "<div class='chart-box'>",
                                        unsafe_allow_html=True
                                    )
                                    st.write(
                                        "**Emotion Distribution**"
                                    )

                                    fig = donut_chart(
                                        r["emotion_scores"]
                                    )

                                    if fig:
                                        st.pyplot(
                                            fig,
                                            use_container_width=False
                                        )
                                    else:
                                        st.bar_chart(
                                            r["emotion_scores"]
                                        )
                                    st.markdown(
                                        "</div>",
                                        unsafe_allow_html=True
                                    )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

            elif section == "Journal":

                st.markdown(
                    '<div class="journal-card">'
                    '<div class="journal-header">'
                    '<div class="j-emoji">😍</div>'
                    '<div class="j-title">'
                    'Welcome Back! Let\'s Journal Your Day'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                journal_text = st.text_area(
                    "Write about how you're feeling today",
                    height=150,
                    placeholder="What's making you smile today?",
                )

                if st.button("Analyze my entry"):

                    if not journal_text.strip():
                        st.warning("Write something first.")

                    else:

                        with st.spinner(
                            "Running NLP analysis…"
                        ):

                            try:
                                resp = requests.post(
                                    f"{BACKEND_URL}/analyze-text",
                                    json={"text": journal_text},
                                    headers=headers,
                                    timeout=120,
                                )

                            except requests.exceptions.RequestException as e:
                                st.error(
                                    f"Could not reach backend: {e}"
                                )
                                resp = None

                        if resp is not None:

                            if resp.status_code != 200:
                                st.error("Analysis failed.")

                            else:

                                r = resp.json()

                                confidence = r.get(
                                    "emotion_confidence"
                                )

                                save_mood_log(
                                    user["id"],
                                    r["final_sentiment"],
                                    r["final_emotion"],
                                    r["sentiment_scores"]["compound"],
                                    journal_text,
                                    confidence=confidence,
                                    positive_score=r["sentiment_scores"].get("pos"),
                                    negative_score=r["sentiment_scores"].get("neg"),
                                    neutral_score=r["sentiment_scores"].get("neu"),
                                    detected_language=r.get("detected_language"),
                                    cleaned_text=r.get("cleaned_text"),
                                )

                                conf_str = (
                                    f", Confidence: **{confidence:.0%}**"
                                    if confidence is not None
                                    else ""
                                )

                                st.success(
                                    f"Saved! Sentiment: "
                                    f"**{r['final_sentiment']}**, "
                                    f"Emotion: **{r['final_emotion']}**"
                                    f"{conf_str}"
                                )

                                st.bar_chart(
                                    r["emotion_scores"]
                                )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="journal-card"><h3>📁 Or upload a file</h3></div>',
                    unsafe_allow_html=True
                )

                uploaded = st.file_uploader(
                    "Choose a CSV or TXT file",
                    type=["csv", "txt"]
                )

                if uploaded is not None and st.button(
                    "Run NLP Analysis on file"
                ):

                    files = {
                        "file": (
                            uploaded.name,
                            uploaded.getvalue()
                        )
                    }

                    with st.spinner(
                        "Running multilingual NLP pipeline…"
                    ):

                        try:
                            resp = requests.post(
                                f"{BACKEND_URL}/analyze",
                                files=files,
                                headers=headers,
                                timeout=120
                            )

                        except requests.exceptions.RequestException as e:
                            st.error(
                                f"Could not reach backend: {e}"
                            )
                            resp = None

                    if resp is not None:

                        if resp.status_code != 200:
                            st.error("Analysis failed.")

                        else:

                            r = resp.json()

                            confidence = r.get(
                                "emotion_confidence"
                            )

                            save_mood_log(
                                user["id"],
                                r["final_sentiment"],
                                r["final_emotion"],
                                r["sentiment_scores"]["compound"],
                                r.get("cleaned_text", ""),
                                confidence=confidence,
                                positive_score=r["sentiment_scores"].get("pos"),
                                negative_score=r["sentiment_scores"].get("neg"),
                                neutral_score=r["sentiment_scores"].get("neu"),
                                detected_language=r.get("detected_language"),
                                cleaned_text=r.get("cleaned_text"),
                            )

                            conf_str = (
                                f", Confidence: **{confidence:.0%}**"
                                if confidence is not None
                                else ""
                            )

                            st.success(
                                f"Saved! Sentiment: "
                                f"**{r['final_sentiment']}**, "
                                f"Emotion: **{r['final_emotion']}**"
                                f"{conf_str}"
                            )

                            st.bar_chart(
                                r["emotion_scores"]
                            )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="journal-card"><h3>📜 Past entries</h3></div>',
                    unsafe_allow_html=True
                )

                history = [
                    h
                    for h in get_user_mood_history(
                        user["id"],
                        limit=20
                    )
                    if h["journal_text"]
                ]

                if not history:
                    st.caption(
                        "No journal entries yet."
                    )

                for h in history:

                    s = style_for(
                        h["sentiment"]
                    )

                    conf_str = (
                        f" · Confidence: "
                        f"{h['confidence']:.0%}"
                        if h.get("confidence") is not None
                        else ""
                    )

                    with st.expander(
                        f"{s['emoji']} "
                        f"{h['sentiment']} — "
                        f"{h['created_at'].strftime('%Y-%m-%d %H:%M')}"
                        f"{conf_str}"
                    ):
                        st.write(
                            h["journal_text"]
                        )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

            elif section == "Face Recognition":

                st.markdown(
                    "<div class='mm-card'><h3>😊 Face Recognition</h3></div>",
                    unsafe_allow_html=True
                )

                st.caption(
                    "Allow camera access to capture your face."
                )

                st.subheader("🔐 Face Recognition")

                option = st.radio(
                    "Choose an option:",
                    ["📷 Camera", "📁 Upload Image"],
                    horizontal=True
                )

                camera_image = None
                uploaded_image = None

                if option == "📷 Camera":
                    camera_image = st.camera_input("Take a photo")

                elif option == "📁 Upload Image":
                    uploaded_image = st.file_uploader(
                        "Choose an image",
                        type=["jpg", "jpeg", "png"]
                    )

                    if uploaded_image is not None:
                        st.image(
                            uploaded_image,
                            caption="Selected Image",
                            width=300
                        )

                    st.write("")

                    analyze_face = st.button(
                        "🔍 Analyze Face",
                        type="primary",
                        use_container_width=True
                    )

                    if analyze_face:

                        with st.spinner(
                            "Analyzing your face..."
                        ):

                            try:

                                import tempfile
                                from deepface import DeepFace

                                # Uploaded image bytes
                                image_bytes = uploaded_image.getvalue()

                                with tempfile.NamedTemporaryFile(
                                    delete=False,
                                    suffix=".jpg"
                                ) as tmp_file:

                                    tmp_file.write(image_bytes)
                                    image_path = tmp_file.name

                                result = DeepFace.analyze(
                                    img_path=image_path,
                                    actions=["emotion"],
                                    enforce_detection=False
                                )

                                if isinstance(result, list):
                                    result = result[0]

                                emotion = result.get(
                                    "dominant_emotion",
                                    "Unknown"
                                )

                                emotion_scores = result.get(
                                    "emotion",
                                    {}
                                )

                                st.success(
                                    "✅ Face analyzed successfully!"
                                )

                                st.subheader("😊 Emotion Analysis")

                                # Display emotion percentages
                                st.write(
                                    f"😊 Happy: **{emotion_scores.get('happy', 0):.2f}%**"
                                )

                                st.progress(
                                    int(emotion_scores.get("happy", 0))
                                )

                                st.write(
                                    f"😢 Sad: **{emotion_scores.get('sad', 0):.2f}%**"
                                )

                                st.progress(
                                    int(emotion_scores.get("sad", 0))
                                )

                                st.write(
                                    f"😠 Angry: **{emotion_scores.get('angry', 0):.2f}%**"
                                )

                                st.progress(
                                    int(emotion_scores.get("angry", 0))
                                )

                                st.write(
                                    f"😐 Neutral: **{emotion_scores.get('neutral', 0):.2f}%**"
                                )

                                st.progress(
                                    int(emotion_scores.get("neutral", 0))
                                )

                                st.write(
                                    f"😨 Fear: **{emotion_scores.get('fear', 0):.2f}%**"
                                )

                                st.progress(
                                    int(emotion_scores.get("fear", 0))
                                )

                                st.write(
                                    f"🤢 Disgust: **{emotion_scores.get('disgust', 0):.2f}%**"
                                )

                                st.progress(
                                    int(emotion_scores.get("disgust", 0))
                                )

                                st.write(
                                    f"😲 Surprise: **{emotion_scores.get('surprise', 0):.2f}%**"
                                )

                                st.progress(
                                    int(emotion_scores.get("surprise", 0))
                                )




                                st.caption(
                                    "The percentage represents the model's "
                                    "confidence for the detected emotion."
                                )

                            except Exception as e:

                                st.error(
                                    "Unable to analyze the face."
                                )

                                st.code(
                                    str(e)
                                )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

            elif section == "Wellness Chat":

                st.markdown(
                    "<div class='mm-card'><h3>💬 Wellness Chat</h3></div>",
                    unsafe_allow_html=True
                )

                st.caption(
                    "A supportive space to talk about how you're feeling. "
                    "Not a substitute for professional care."
                )

                chat_box = st.container(
                    height=450
                )

                with chat_box:

                    for turn in st.session_state.chat_history:

                        with st.chat_message(
                            turn["role"]
                        ):

                            st.write(
                                turn["content"]
                            )

                user_msg = st.chat_input(
                    "How are you feeling today?"
                )

                if user_msg:

                    st.session_state.chat_history.append(
                        {
                            "role": "user",
                            "content": user_msg
                        }
                    )

                    recent_history = (
                        st.session_state.chat_history[-10:-1]
                    )

                    try:

                        resp = requests.post(
                            f"{BACKEND_URL}/chat",
                            json={
                                "message": user_msg,
                                "history": recent_history
                            },
                            headers=headers,
                            timeout=60
                        )

                        reply = (
                            resp.json()["reply"]
                            if resp.status_code == 200
                            else
                            "Sorry, I couldn't reach the wellness assistant right now."
                        )

                    except requests.exceptions.RequestException:

                        reply = (
                            "Sorry, I couldn't reach the wellness assistant right now."
                        )

                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": reply
                        }
                    )

                    st.rerun()

                if (
                    st.session_state.chat_history
                    and st.button("Clear chat")
                ):

                    st.session_state.chat_history = []

                    st.rerun()

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

            elif section == "Weekly Report":

                st.markdown(
                    "<div class='mm-card'><h3>📊 Weekly Wellness Report</h3></div>",
                    unsafe_allow_html=True
                )

                st.caption(
                    "A holistic 7-day assessment using actual stored mood, "
                    "journal/NLP, stress, sleep, workload and journal "
                    "consistency data. Missing values are never treated as zero."
                )

                end_date = st.date_input(
                    "Report end date",
                    value=date.today(),
                    key="weekly_end_date"
                )

                start_date = (
                    end_date
                    - __import__('datetime').timedelta(days=6)
                )

                st.caption(
                    f"Selected period: "
                    f"{start_date} → {end_date}"
                )

                with st.expander(
                    "⚙️ Configure scoring weights",
                    expanded=False
                ):

                    weight_values = {}
                    weight_cols = st.columns(2)

                    for idx, (
                        name,
                        default
                    ) in enumerate(
                        DEFAULT_WEEKLY_WEIGHTS.items()
                    ):

                        with weight_cols[idx % 2]:

                            weight_values[name] = st.slider(
                                name,
                                0,
                                50,
                                int(default),
                                1,
                                key=f"weekly_weight_{name}"
                            )

                    st.caption(
                        "Weights are normalized automatically across "
                        "the components that actually have data. "
                        "A missing component is not scored as zero."
                    )

                report = build_weekly_report_data(
                    user["id"],
                    end_date,
                    get_user_mood_history,
                    get_daily_wellness_range
                )

                stats = aggregate_week(
                    report["days"],
                    weight_values
                )

                if stats["coverage_days"] == 0:

                    st.info(
                        "No wellness information is stored for this "
                        "7-day period yet. Add a mood, journal entry, "
                        "or daily wellness details to generate the report."
                    )

                else:

                    score = stats["weekly_score"]

                    status = (
                        "Excellent"
                        if score is not None and score >= 85
                        else
                        "Good"
                        if score is not None and score >= 70
                        else
                        "Needs Attention"
                        if score is not None
                        else
                        "Unavailable"
                    )

                    m1, m2, m3, m4 = st.columns(4)

                    with m1:
                        metric_tile(
                            "Wellness Score",
                            f"{score:.0f} / 100"
                            if score is not None
                            else "—",
                            status
                        )

                    with m2:
                        metric_tile(
                            "Data Coverage",
                            f"{stats['coverage_days']} / 7",
                            f"{stats['coverage_pct']:.2f}%"
                        )

                    with m3:
                        metric_tile(
                            "Average Stress",
                            f"{stats['avg_stress']:.1f} / 10"
                            if stats.get("avg_stress") is not None
                            else "—"
                        )

                    with m4:
                        metric_tile(
                            "Average Sleep",
                            f"{stats['avg_sleep']:.1f} hrs"
                            if stats.get("avg_sleep") is not None
                            else "—"
                        )

                    m5, m6, m7, m8 = st.columns(4)

                    with m5:
                        metric_tile(
                            "Most Common Mood",
                            stats.get("most_common_mood") or "—"
                        )

                    with m6:
                        metric_tile(
                            "Most Common Emotion",
                            stats.get("most_common_emotion") or "—"
                        )

                    with m7:
                        metric_tile(
                            "Journal Activity",
                            f"{stats['journal_days']} / 7",
                            f"{stats['journal_consistency']:.2f}%"
                        )

                    with m8:
                        metric_tile(
                            "Emotion Confidence",
                            f"{stats['avg_emotion_confidence']:.1%}"
                            if stats.get("avg_emotion_confidence") is not None
                            else "—"
                        )

                    st.markdown(
                        "### 📅 Daily Wellness Scores"
                    )

                    table_rows = []

                    for d in report["days"]:

                        table_rows.append(
                            {
                                "Date": str(d["date"]),
                                "Mood": d.get("mood") or "—",
                                "Emotion": d.get("emotion") or "—",
                                "Stress":
                                    f"{d['stress_level']:.1f}/10"
                                    if d.get("stress_level") is not None
                                    else "—",
                                "Sleep":
                                    f"{d['sleep_hours']:.1f} h"
                                    if d.get("sleep_hours") is not None
                                    else "—",
                                "Workload":
                                    d.get("workload") or "—",
                                "Journal":
                                    "Yes"
                                    if d.get("has_journal")
                                    else "No",
                                "Daily Score":
                                    f"{d['daily_score']:.1f}"
                                    if d.get("daily_score") is not None
                                    else "—",
                            }
                        )

                    st.dataframe(
                        table_rows,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.markdown(
                        "### 📈 Weekly Charts"
                    )

                    dates = [
                        d["date"].strftime("%a %d")
                        for d in report["days"]
                    ]

                    mood_numeric = [
                        MOOD_TO_NUM.get(
                            d.get("mood"),
                            None
                        )
                        for d in report["days"]
                    ]

                    stress_series = [
                        d.get("stress_level")
                        for d in report["days"]
                    ]

                    sleep_series = [
                        d.get("sleep_hours")
                        for d in report["days"]
                    ]

                    score_series = [
                        d.get("daily_score")
                        for d in report["days"]
                    ]

                    c1, c2 = st.columns(2)
                    figures = []

                    with c1:

                        st.markdown(
                            "<div class='chart-box'>",
                            unsafe_allow_html=True
                        )

                        fig1, ax1 = plt.subplots(
                            figsize=(6, 3.2)
                        )

                        ax1.plot(
                            dates,
                            [
                                v
                                if v is not None
                                else float('nan')
                                for v in mood_numeric
                            ],
                            marker="o"
                        )

                        ax1.set_title(
                            "Mood Trend"
                        )

                        ax1.set_ylabel(
                            "Mood score"
                        )

                        ax1.grid(
                            alpha=0.2
                        )

                        fig1.tight_layout()

                        st.pyplot(
                            fig1,
                            use_container_width=True
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                        figures.append(
                            ("Mood Trend", fig1)
                        )

                    with c2:

                        st.markdown(
                            "<div class='chart-box'>",
                            unsafe_allow_html=True
                        )

                        fig2, ax2 = plt.subplots(
                            figsize=(6, 3.2)
                        )

                        ax2.plot(
                            dates,
                            [
                                v
                                if v is not None
                                else float('nan')
                                for v in stress_series
                            ],
                            marker="o"
                        )

                        ax2.set_title(
                            "Stress Trend"
                        )

                        ax2.set_ylabel(
                            "Stress / 10"
                        )

                        ax2.grid(
                            alpha=0.2
                        )

                        fig2.tight_layout()

                        st.pyplot(
                            fig2,
                            use_container_width=True
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                        figures.append(
                            ("Stress Trend", fig2)
                        )

                    c3, c4 = st.columns(2)

                    with c3:

                        st.markdown(
                            "<div class='chart-box'>",
                            unsafe_allow_html=True
                        )

                        fig3, ax3 = plt.subplots(
                            figsize=(6, 3.2)
                        )

                        ax3.plot(
                            dates,
                            [
                                v
                                if v is not None
                                else float('nan')
                                for v in sleep_series
                            ],
                            marker="o"
                        )

                        ax3.set_title(
                            "Sleep Trend"
                        )

                        ax3.set_ylabel(
                            "Hours"
                        )

                        ax3.grid(
                            alpha=0.2
                        )

                        fig3.tight_layout()

                        st.pyplot(
                            fig3,
                            use_container_width=True
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                        figures.append(
                            ("Sleep Trend", fig3)
                        )

                    with c4:

                        st.markdown(
                            "<div class='chart-box'>",
                            unsafe_allow_html=True
                        )

                        fig4, ax4 = plt.subplots(
                            figsize=(6, 3.2)
                        )

                        emo_counts = (
                            stats.get("emotion_counts")
                            or {}
                        )

                        if emo_counts:
                            ax4.pie(
                                list(emo_counts.values()),
                                labels=list(emo_counts.keys()),
                                autopct="%1.0f%%"
                            )
                        else:
                            ax4.text(
                                0.5,
                                0.5,
                                "No emotion data",
                                ha="center",
                                va="center"
                            )

                        ax4.set_title(
                            "Emotion Distribution"
                        )

                        fig4.tight_layout()

                        st.pyplot(
                            fig4,
                            use_container_width=True
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                        figures.append(
                            (
                                "Emotion Distribution",
                                fig4
                            )
                        )

                    c5, c6 = st.columns(2)

                    with c5:

                        st.markdown(
                            "<div class='chart-box'>",
                            unsafe_allow_html=True
                        )

                        fig5, ax5 = plt.subplots(
                            figsize=(6, 3.2)
                        )

                        emo_counts = (
                            stats.get("emotion_counts")
                            or {}
                        )

                        if emo_counts:
                            ax5.bar(
                                list(emo_counts.keys()),
                                list(emo_counts.values())
                            )
                        else:
                            ax5.text(
                                0.5,
                                0.5,
                                "No emotion data",
                                ha="center",
                                va="center"
                            )

                        ax5.set_title(
                            "Emotion Frequency"
                        )

                        ax5.tick_params(
                            axis="x",
                            rotation=30
                        )

                        fig5.tight_layout()

                        st.pyplot(
                            fig5,
                            use_container_width=True
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                        figures.append(
                            (
                                "Emotion Frequency",
                                fig5
                            )
                        )

                    with c6:

                        st.markdown(
                            "<div class='chart-box'>",
                            unsafe_allow_html=True
                        )

                        labels = [
                            "Positive",
                            "Negative",
                            "Neutral",
                            "Compound"
                        ]

                        vals = [
                            stats.get("avg_positive"),
                            stats.get("avg_negative"),
                            stats.get("avg_neutral"),
                            stats.get("avg_compound")
                        ]

                        if all(
                            v is None
                            for v in vals
                        ):
                            vals = [
                                0,
                                0,
                                0,
                                0
                            ]
                        else:
                            vals = [
                                0 if v is None else v
                                for v in vals
                            ]

                        fig6, ax6 = plt.subplots(
                            figsize=(6, 3.2)
                        )

                        ax6.bar(
                            labels,
                            vals
                        )

                        ax6.set_title(
                            "Sentiment Analysis"
                        )

                        ax6.grid(
                            axis="y",
                            alpha=0.2
                        )

                        fig6.tight_layout()

                        st.pyplot(
                            fig6,
                            use_container_width=True
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                        figures.append(
                            (
                                "Sentiment Analysis",
                                fig6
                            )
                        )

                    st.markdown(
                        "<div class='chart-box'>",
                        unsafe_allow_html=True
                    )

                    fig7, ax7 = plt.subplots(
                        figsize=(12, 3.2)
                    )

                    ax7.plot(
                        dates,
                        [
                            v
                            if v is not None
                            else float('nan')
                            for v in score_series
                        ],
                        marker="o"
                    )

                    ax7.set_title(
                        "Wellness Score Trend"
                    )

                    ax7.set_ylabel(
                        "Score / 100"
                    )

                    ax7.grid(
                        alpha=0.2
                    )

                    fig7.tight_layout()

                    st.pyplot(
                        fig7,
                        use_container_width=True
                    )

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True
                    )

                    figures.append(
                        (
                            "Wellness Score Trend",
                            fig7
                        )
                    )

                    st.markdown(
                        "### 🔎 Detailed Analysis"
                    )

                    a1, a2, a3 = st.columns(3)

                    with a1:

                        st.metric(
                            "Avg Stress",
                            f"{stats['avg_stress']:.1f}/10"
                            if stats.get("avg_stress") is not None
                            else "Unavailable"
                        )

                        if stats.get("stress_trend"):
                            st.caption(
                                f"Trend: {stats['stress_trend']}"
                            )

                        if (
                            stats.get("avg_stress") is not None
                            and stats["avg_stress"] >= 7
                        ):
                            st.warning(
                                "⚠ High average stress"
                            )

                    with a2:

                        st.metric(
                            "Avg Sleep",
                            f"{stats['avg_sleep']:.1f} hrs"
                            if stats.get("avg_sleep") is not None
                            else "Unavailable"
                        )

                        if (
                            stats.get("avg_sleep") is not None
                            and stats["avg_sleep"] < 6
                        ):
                            st.warning(
                                "⚠ Low average sleep"
                            )

                        if stats.get(
                            "sleep_consistency"
                        ) is not None:
                            st.caption(
                                f"Sleep consistency: "
                                f"{stats['sleep_consistency']:.1f}%"
                            )

                    with a3:

                        st.metric(
                            "High Workload Days",
                            stats.get(
                                "high_workload_days",
                                0
                            )
                        )

                        st.caption(
                            str(
                                stats.get(
                                    "workload_counts"
                                )
                                or "No workload data"
                            )
                        )

                    st.markdown(
                        "### 🤖 AI Weekly Summary"
                    )

                    base_summary = generate_weekly_summary(
                        stats
                    )

                    ai_summary = None

                    ai_prompt = (
                        "Write a concise employee wellness "
                        "weekly summary using ONLY these actual "
                        "stored values. Do not invent missing "
                        "values and do not diagnose the employee. "
                        + base_summary
                        + " "
                        + str(stats)
                    )

                    try:

                        ai_resp = requests.post(
                            f"{BACKEND_URL}/chat",
                            json={
                                "message": ai_prompt,
                                "history": []
                            },
                            headers=headers,
                            timeout=60
                        )

                        if ai_resp.status_code == 200:
                            ai_summary = (
                                ai_resp.json().get(
                                    "reply"
                                )
                            )

                    except requests.exceptions.RequestException:
                        ai_summary = None

                    summary = (
                        ai_summary.strip()
                        if ai_summary
                        else base_summary
                    )

                    st.info(
                        summary
                    )

                    recs = recommendations(
                        stats
                    )

                    awards = achievements(
                        stats
                    )

                    r1, r2 = st.columns(2)

                    with r1:

                        st.markdown(
                            "### 💡 Personalized Recommendations"
                        )

                        for item in recs:
                            st.write(
                                "• " + item
                            )

                    with r2:

                        st.markdown(
                            "### 🏆 Achievements"
                        )

                        for item in awards:
                            st.write(
                                item
                            )

                    st.markdown(
                        "### 📄 Download Weekly Wellness Report"
                    )

                    pdf_bytes = build_weekly_pdf(
                        user["username"],
                        user["email"],
                        report,
                        stats,
                        summary,
                        recs,
                        awards,
                        figures
                    )

                    st.download_button(
                        "Download Weekly Wellness Report PDF",
                        data=pdf_bytes,
                        file_name=(
                            f"weekly_wellness_"
                            f"{start_date}_{end_date}.pdf"
                        ),
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

                    for _, fig in figures:
                        plt.close(fig)

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

            elif section == "Dashboard":

                history = get_user_mood_history(
                    user["id"],
                    limit=200
                )

                if not history:

                    st.info(
                        "No entries yet — pick a mood on Home "
                        "or write a journal entry to see your dashboard."
                    )

                else:

                    counts = {
                        label: 0
                        for label in MOOD_LABELS
                    }

                    for h in history:

                        if h["sentiment"] in counts:
                            counts[h["sentiment"]] += 1

                    c1, c2 = st.columns(2)

                    with c1:

                        st.markdown(
                            f"<div class='chart-box'><h4 style='margin-top:0;color:{TITLE_COLOR}'>Mood distribution</h4>",
                            unsafe_allow_html=True
                        )

                        fig = donut_chart(
                            counts
                        )

                        if fig:

                            st.pyplot(
                                fig,
                                use_container_width=False
                            )

                        else:

                            st.bar_chart(
                                counts
                            )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                    with c2:

                        st.markdown(
                            f"<div class='chart-box'><h4 style='margin-top:0;color:{TITLE_COLOR}'>Mood trend over time</h4>",
                            unsafe_allow_html=True
                        )

                        by_date = {}

                        for h in history:

                            d = h["mood_date"]

                            by_date.setdefault(
                                d,
                                []
                            ).append(
                                MOOD_TO_NUM.get(
                                    h["sentiment"],
                                    0
                                )
                            )

                        trend = {
                            str(d):
                            sum(v) / len(v)
                            for d, v in sorted(
                                by_date.items()
                            )
                        }

                        st.line_chart(
                            trend
                        )

                        st.markdown(
                            "</div>",
                            unsafe_allow_html=True
                        )

                    st.markdown(
                        f"<div class='chart-box'><h4 style='margin-top:0;color:{TITLE_COLOR}'>Emotions detected from journal entries</h4>",
                        unsafe_allow_html=True
                    )

                    emo_counts = {}

                    for h in history:

                        if (
                            h["source"] == "nlp"
                            and h["emotion"]
                        ):

                            emo_counts[h["emotion"]] = (
                                emo_counts.get(
                                    h["emotion"],
                                    0
                                ) + 1
                            )

                    if emo_counts:

                        st.bar_chart(
                            emo_counts
                        )

                    else:

                        st.caption(
                            "No journal-based emotion data yet."
                        )

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "<div class='mm-card'><h4>Recent activity</h4></div>",
                        unsafe_allow_html=True
                    )

                    table_rows = [
                        {
                            "Date": h["mood_date"],
                            "Time": h["created_at"].strftime(
                                "%H:%M"
                            ),
                            "Mood":
                                f"{style_for(h['sentiment'])['emoji']} "
                                f"{h['sentiment']}",
                            "Confidence":
                                f"{h['confidence']:.0%}"
                                if h.get("confidence") is not None
                                else "—",
                            "Source": h["source"],
                        }
                        for h in history[:15]
                    ]

                    st.dataframe(
                        table_rows,
                        use_container_width=True
                    )

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True
                    )

                st.markdown(
                    "<div class='mm-card'><h4>Team mood trend (last 30 days)</h4></div>",
                    unsafe_allow_html=True
                )

                history = get_all_employee_mood_logs(
                    limit_days=30
                )

                if not history:

                    st.info(
                        "Not enough data yet to draw a trend chart."
                    )

                else:

                    by_date = {}

                    for row in history:

                        d = row["mood_date"]

                        by_date.setdefault(
                            d,
                            []
                        ).append(
                            MOOD_TO_NUM.get(
                                row["sentiment"],
                                0
                            )
                        )

                    trend = {
                        str(d):
                        sum(v) / len(v)
                        for d, v
                        in sorted(
                            by_date.items()
                        )
                    }

                    st.line_chart(
                        trend
                    )

                    st.caption(
                        "Average mood score per day across all employees "
                        "(2 = Amazing, 1 = Happy, 0 = Normal, -1 = Sad, -2 = Angry)"
                    )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

        elif role == "manager":

            st.markdown(
                "<div class='mm-card'><h3>📊 Team Wellness Reports</h3></div>",
                unsafe_allow_html=True
            )

            latest_per_employee = get_latest_mood_per_employee()
            history = get_all_employee_mood_logs(limit_days=30)

            if not latest_per_employee:

                st.info("No employee mood data yet.")

            else:

                total = len(latest_per_employee)

                positive = sum(
                    1 for r in latest_per_employee
                    if r["sentiment"] in ("Amazing", "Happy")
                )

                m1, m2, m3 = st.columns(3)

                with m1:
                    metric_tile("Employees Tracked", total)

                with m2:
                    metric_tile("Positive Latest Mood", f"{positive}/{total}")

                with m3:
                    metric_tile("Entries (30 days)", len(history))

                st.markdown("### Latest mood per employee")

                st.dataframe(
                    [
                        {
                            "Employee": r["username"],
                            "Email": r["email"],
                            "Date": r["mood_date"],
                            "Mood": f"{style_for(r['sentiment'])['emoji']} {r['sentiment']}",
                            "Confidence":
                                f"{r['confidence']:.0%}"
                                if r.get("confidence") is not None
                                else "—",
                            "Last updated": r["created_at"].strftime("%Y-%m-%d %H:%M"),
                        }
                        for r in latest_per_employee
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown(
                "<div class='mm-card'><h4>Team mood trend (last 30 days)</h4></div>",
                unsafe_allow_html=True
            )

            if not history:

                st.info("Not enough data yet to draw a trend chart.")

            else:

                by_date = {}

                for row in history:
                    by_date.setdefault(
                        row["mood_date"], []
                    ).append(MOOD_TO_NUM.get(row["sentiment"], 0))

                trend = {
                    str(d): sum(v) / len(v)
                    for d, v in sorted(by_date.items())
                }

                st.line_chart(trend)

                st.caption(
                    "Average mood score per day across all employees "
                    "(2 = Amazing, 1 = Happy, 0 = Normal, -1 = Sad, -2 = Angry)"
                )

            st.markdown("</div>", unsafe_allow_html=True)

        st.stop()


# ============================================================
# WELCOME / LOGIN SCREEN
# ============================================================
if st.session_state.page == "welcome":

    if "quote" not in st.session_state:
        st.session_state.quote = random.choice(QUOTES)

    hour = datetime.now().hour
    greeting = "Good Morning" if hour < 12 else ("Good Afternoon" if hour < 18 else "Good Evening")

    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            '<div class="login-shell" style="padding:32px 36px;">'
            '<span class="login-blob-1"></span><span class="login-blob-2"></span>'
            '<span class="sparkle" style="top:18px;right:30px;animation-delay:0s">✨</span>'
            '<span class="sparkle" style="top:52px;right:64px;animation-delay:0.8s">✨</span>'
            "<div class='brand-row'>✨ MoodMentor</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='quote-box'>\" {st.session_state.quote} \"</div>",
            unsafe_allow_html=True,
        )

        mode = st.session_state.auth_mode

        if mode == "login":
            st.markdown(f"<div class='greet-title'>{greeting},</div>", unsafe_allow_html=True)
            st.markdown("<div class='greet-sub'>Let's check in on your well-being today.</div>", unsafe_allow_html=True)

            email = st.text_input("Email Address", placeholder="Enter your email", label_visibility="collapsed", key="login_email")
            pw = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="collapsed", key="login_pw")
            keep_signed_in = st.checkbox("Keep me signed in", value=True)

            if st.button("Continue to Dashboard 🚀", type="primary", use_container_width=True):
                u = get_user(email.strip().lower())
                if not u or not check_pw(pw, u["password_hash"]):
                    st.error("Invalid email or password.")
                elif not u["is_verified"]:
                    st.warning("Verify your email first.")
                    st.session_state.email = u["email"]; goto_auth("verify")
                else:
                    st.session_state.token = make_token(u)
                    st.rerun()

            st.markdown("<div class='divider-text'>or continue with</div>", unsafe_allow_html=True)
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("🌐 Google", use_container_width=True):
                    st.info("Google sign-in isn't connected yet — use email/password for now.")
            with sc2:
                if st.button("🍏 Apple", use_container_width=True):
                    st.info("Apple sign-in isn't connected yet — use email/password for now.")

            st.write("")
            st.markdown(
                f"<div style='text-align:center;color:{MUTED};font-weight:600'>New to MoodMentor?</div>",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Create an account", use_container_width=True): goto_auth("signup")
            with c2:
                if st.button("Forgot password?", use_container_width=True): goto_auth("forgot")

        elif mode == "signup":
            st.markdown("<div class='greet-title'>Create Account</div>", unsafe_allow_html=True)
            st.markdown("<div class='greet-sub'>Let's get you started.</div>", unsafe_allow_html=True)
            with st.form("signup"):
                username = st.text_input("Full Name", placeholder="Enter your full name")
                email = st.text_input("Email", placeholder="Enter your email")
                pw = st.text_input("Password", type="password", placeholder="Create password")
                role_label = st.radio("I am signing up as a:", ["Employee", "Manager"], horizontal=True)
                go = st.form_submit_button("Send OTP 🚀", type="primary", use_container_width=True)
            if go:
                email = email.strip().lower()
                role = "manager" if role_label == "Manager" else "employee"
                if len(username) < 3:
                    st.error("Username too short.")
                elif not valid_pw(pw):
                    st.error("Password needs 8+ chars, letters and numbers.")
                elif username_taken(username) or get_user(email):
                    st.error("Username or email already in use.")
                else:
                    create_user(username, email, pw, role=role)
                    code = new_otp(); save_otp(email, code, "signup")
                    ok, msg = send_otp(email, code, "signup")
                    if ok:
                        st.session_state.email = email
                        st.success("Check your email for the code.")
                        goto_auth("verify")
                    else:
                        st.error(f"Email failed: {msg}")
            if st.button("Already have an account? Login"): goto_auth("login")

        elif mode == "verify":
            email = st.session_state.email
            st.markdown("<div class='greet-title'>Verify OTP</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='greet-sub'>We have sent a 6-digit code to {email}</div>", unsafe_allow_html=True)
            with st.form("verify"):
                code = st.text_input("Code", max_chars=6, placeholder="Enter 6-digit code")
                go = st.form_submit_button("Verify OTP", type="primary", use_container_width=True)
            if go:
                if check_otp(email, code.strip(), "signup"):
                    verify_user(email)
                    st.success("Verified! Please log in.")
                    goto_auth("login")
                else:
                    st.error("Invalid or expired code.")
            if st.button("← Back to login"): goto_auth("login")

        elif mode == "forgot":
            st.markdown("<div class='greet-title'>🔑 Forgot password</div>", unsafe_allow_html=True)
            with st.form("forgot"):
                email = st.text_input("Your account email")
                go = st.form_submit_button("Send reset code", type="primary", use_container_width=True)
            if go:
                email = email.strip().lower()
                if get_user(email):
                    code = new_otp(); save_otp(email, code, "password_reset")
                    send_otp(email, code, "password_reset")
                st.session_state.email = email
                st.info("If that email exists, a code was sent.")
                goto_auth("reset")
            if st.button("← Back to login"): goto_auth("login")

        elif mode == "reset":
            email = st.session_state.email
            st.markdown("<div class='greet-title'>🔄 Reset password</div>", unsafe_allow_html=True)
            with st.form("reset"):
                code = st.text_input("Reset code", max_chars=6)
                pw = st.text_input("New password", type="password")
                go = st.form_submit_button("Reset", type="primary", use_container_width=True)
            if go:
                if not valid_pw(pw):
                    st.error("Password needs 8+ chars, letters and numbers.")
                elif not check_otp(email, code.strip(), "password_reset"):
                    st.error("Invalid or expired code.")
                else:
                    set_password(email, pw)
                    st.success("Password reset. Please log in.")
                    goto_auth("login")
            if st.button("← Back to login"): goto_auth("login")

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        hero_html = (
            '<div style="position:relative; overflow:hidden; border-radius:32px; height:100%; '
            'min-height:680px; padding:0; '
            'box-shadow:0 34px 80px -18px rgba(99,102,241,0.35); '
            'border: 1.5px solid rgba(255,255,255,0.7); '
            'display:flex; flex-direction:column;">'

            # ---- BIG hero image filling the panel ----
            f'<img src="data:image/jpeg;base64,{WELCOME_IMAGE_B64}" '
            'style="width:100%; height:100%; object-fit:cover; '
            'position:absolute; inset:0; z-index:0; display:block;" />'

            # subtle top gradient so the badge stays readable over the photo
            '<div style="position:absolute; top:0; left:0; right:0; height:120px; z-index:1; '
            'background:linear-gradient(180deg, rgba(0,0,0,0.28), transparent);"></div>'

            # AI-powered wellness badge, top-left over the image
            '<div style="position:relative; z-index:2; padding:20px 24px 0 24px;">'
            '<span class="hero-badge">🧠 &nbsp;AI-Powered Wellness</span>'
            '</div>'

            # spacer to push the review card to the bottom
            '<div style="flex:1;"></div>'

            # review card, overlapping the bottom of the image
            '<div style="position:relative; z-index:2; margin:0 20px 20px 20px; '
            'background:rgba(255,255,255,0.95); backdrop-filter:blur(16px); '
            'padding:18px 22px; border-radius:22px; border:1.5px solid rgba(255,255,255,0.95); '
            'box-shadow:0 18px 40px -14px rgba(99,102,241,0.35);">'
            '<div class="stars-twinkle" style="color:#F59E0B; font-size:1.05rem; margin-bottom:7px; letter-spacing:2px;">★★★★★</div>'
            '<div style="font-size:0.88rem; font-weight:500; color:#1E1B2E; line-height:1.55; margin-bottom:12px;">'
            '"MoodMentor made checking in on myself feel light, not like a chore."</div>'
            '<div style="display:flex;align-items:center;gap:9px;">'
            '<div style="width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#EC4899,#9F7AEA);'
            'color:white;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;'
            'box-shadow:0 4px 10px -2px rgba(236,72,153,0.5);">S</div>'
            f'<div style="font-size:0.82rem; font-weight:800; color:{TITLE_COLOR};">Sarah Jenkins</div>'
            f'<div style="font-size:0.75rem; font-weight:600; color:{MUTED}; margin-left:auto;">Verified user</div>'
            '</div></div>'

            '</div>'
        )
        st.markdown(hero_html, unsafe_allow_html=True)

    st.stop()