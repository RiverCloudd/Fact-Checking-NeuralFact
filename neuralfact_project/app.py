import streamlit as st
import time
from pipeline.nodes import decompose_node, checkworthy_node, retrieve_node, verify_node
from core.config import PRICE_1M_INPUT_TOKENS, PRICE_1M_OUTPUT_TOKENS


def _display_evidence_text(ev) -> str:
    if isinstance(ev, dict):
        return str(ev.get("text", "")).strip()
    return str(ev or "").strip()


ICON_CHECK = '<span class="nf-icon">&#xf00c;</span>'
ICON_FAIL = '<span class="nf-icon">&#xf00d;</span>'
ICON_WARN = '<span class="nf-icon">&#xf071;</span>'
ICON_EVID = '<span class="nf-icon">&#xf02d;</span>'
ICON_DETAIL = '<span class="nf-icon">&#xf201;</span>'
ICON_SUMMARY = '<span class="nf-icon">&#xf15c;</span>'


def _inject_modern_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

            @font-face {
                font-family: 'NerdFontSymbolsWeb';
                src: url('https://cdn.jsdelivr.net/gh/ryanoasis/nerd-fonts@master/patched-fonts/NerdFontsSymbolsOnly/SymbolsNerdFont-Regular.ttf') format('truetype');
                font-weight: normal;
                font-style: normal;
                font-display: swap;
            }

            :root {
                --bg-a: #081425;
                --bg-b: #0a1d36;
                --bg-c: #102844;
                --card: rgba(12, 29, 49, 0.82);
                --text-main: #d9e9ff;
                --text-soft: #9bb4d3;
                --ring: rgba(34, 211, 238, 0.28);
                --box-bg: rgba(10, 30, 50, 0.9);
                --box-border: rgba(125, 211, 252, 0.36);
                --box-shadow: 0 12px 24px rgba(4, 16, 30, 0.48);
            }

            .stApp {
                background:
                    radial-gradient(circle at 10% 10%, rgba(45, 212, 191, 0.12) 0%, transparent 35%),
                    radial-gradient(circle at 92% 0%, rgba(56, 189, 248, 0.15) 0%, transparent 38%),
                    linear-gradient(130deg, var(--bg-a) 0%, var(--bg-b) 52%, var(--bg-c) 100%);
                color: var(--text-main);
                font-family: 'IBM Plex Sans', sans-serif;
            }

            .stApp > div[data-testid="stAppViewContainer"] {
                position: relative;
            }

            html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {
                overflow-y: auto !important;
            }

            html, body, .stApp, [data-testid="stAppViewContainer"] {
                overflow-x: hidden !important;
            }

            .tech-bg {
                position: fixed;
                inset: 0;
                pointer-events: none;
                z-index: 0;
                overflow: hidden;
            }

            .tech-badge {
                position: absolute;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 62px;
                height: 62px;
                border-radius: 18px;
                border: 1px solid rgba(125, 241, 255, 0.26);
                background: linear-gradient(135deg, rgba(15, 54, 86, 0.24), rgba(20, 96, 132, 0.18));
                box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.1), 0 8px 26px rgba(3, 22, 40, 0.24);
                backdrop-filter: blur(2px);
                opacity: 0.44;
                will-change: transform;
                animation: techDrift var(--dur, 12s) ease-in-out infinite alternate;
            }

            .tech-logo {
                width: 38px;
                height: 38px;
                object-fit: contain;
                filter: drop-shadow(0 0 5px rgba(191, 238, 255, 0.4));
            }

            .tech-logo.logo-light {
                background: rgba(255, 255, 255, 0.92);
                border-radius: 8px;
                padding: 3px;
                box-sizing: border-box;
            }

            .tech-logo.logo-wide {
                width: 42px;
                height: 42px;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.92);
                padding: 4px;
                box-sizing: border-box;
            }

            .tech-badge.b1 { left: 3%; top: 12%; --dx: 168px; --dy: 124px; --dur: 10s; }
            .tech-badge.b2 { left: 13%; top: 74%; --dx: 196px; --dy: -132px; --dur: 13s; animation-delay: -4s; }
            .tech-badge.b3 { left: 24%; top: 22%; --dx: -164px; --dy: 148px; --dur: 11s; animation-delay: -7s; }
            .tech-badge.b4 { left: 36%; top: 82%; --dx: 174px; --dy: -156px; --dur: 14s; animation-delay: -3s; }
            .tech-badge.b5 { left: 49%; top: 10%; --dx: -182px; --dy: 138px; --dur: 12s; animation-delay: -8s; }
            .tech-badge.b6 { left: 60%; top: 68%; --dx: 208px; --dy: -126px; --dur: 15s; animation-delay: -5s; }
            .tech-badge.b7 { left: 71%; top: 18%; --dx: -172px; --dy: 152px; --dur: 13s; animation-delay: -9s; }
            .tech-badge.b8 { left: 80%; top: 78%; --dx: 158px; --dy: -168px; --dur: 15s; animation-delay: -6s; }
            .tech-badge.b9 { left: 90%; top: 30%; --dx: -198px; --dy: 132px; --dur: 14s; animation-delay: -10s; }
            .tech-badge.b10 { left: 94%; top: 8%; --dx: -166px; --dy: 176px; --dur: 15s; animation-delay: -2s; }

            .block-container {
                position: relative;
                z-index: 1;
            }

            header[data-testid="stHeader"] {
                background: transparent;
                border-bottom: none;
                box-shadow: none;
            }

            [data-testid="stToolbar"] {
                background: transparent !important;
            }

            [data-testid="stHeaderActionElements"] {
                display: none;
            }

            h1, h2, h3 {
                font-family: 'Space Grotesk', sans-serif;
                letter-spacing: -0.01em;
            }

            .block-container {
                max-width: 1100px;
                padding-top: 1.35rem;
                padding-bottom: 2.2rem;
            }

            [data-testid="stDivider"] {
                position: relative;
                height: 2px;
                margin: 1.05rem 0 1.15rem !important;
                border-radius: 999px;
                overflow: hidden;
                background: linear-gradient(90deg, rgba(34, 211, 238, 0.28) 0%, rgba(125, 241, 255, 0.55) 50%, rgba(34, 211, 238, 0.28) 100%) !important;
                box-shadow: 0 0 10px rgba(125, 241, 255, 0.28), 0 0 20px rgba(56, 189, 248, 0.2) !important;
            }

            [data-testid="stDivider"] hr {
                display: none !important;
            }

            [data-testid="stDivider"]::after {
                content: "";
                position: absolute;
                top: -2px;
                left: -32%;
                width: 32%;
                height: 6px;
                background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.98) 50%, transparent 100%);
                filter: drop-shadow(0 0 8px rgba(186, 244, 255, 0.8));
                animation: dividerScan 1.55s linear infinite;
            }

            .stApp hr {
                border: none !important;
                height: 2px !important;
                border-radius: 999px;
                background: linear-gradient(
                    90deg,
                    rgba(34, 211, 238, 0.22) 0%,
                    rgba(125, 241, 255, 0.45) 28%,
                    rgba(255, 255, 255, 0.98) 50%,
                    rgba(125, 241, 255, 0.45) 72%,
                    rgba(34, 211, 238, 0.22) 100%
                ) !important;
                background-size: 240% 100% !important;
                box-shadow: 0 0 12px rgba(125, 241, 255, 0.34), 0 0 22px rgba(56, 189, 248, 0.2) !important;
                animation: resultDividerFlow 1.7s linear infinite;
            }

            .nf-divider {
                position: relative;
                height: 3px;
                border-radius: 999px;
                overflow: hidden;
                margin: 1.08rem 0 1.18rem;
                background: linear-gradient(90deg, rgba(34, 211, 238, 0.28) 0%, rgba(56, 189, 248, 0.62) 50%, rgba(34, 211, 238, 0.28) 100%);
                box-shadow: 0 0 12px rgba(56, 189, 248, 0.32), 0 0 24px rgba(34, 211, 238, 0.2);
            }

            .nf-divider::after {
                content: "";
                position: absolute;
                top: -2px;
                left: -24%;
                width: 24%;
                height: 7px;
                border-radius: 999px;
                background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.98) 50%, transparent 100%);
                filter: blur(0.2px) drop-shadow(0 0 9px rgba(191, 238, 255, 0.95));
                animation: dividerBeam 1.35s linear infinite;
            }

            .hero {
                position: relative;
                isolation: isolate;
                border: 1px solid rgba(103, 232, 249, 0.22);
                border-radius: 24px;
                padding: 1.1rem 1.2rem;
                margin-bottom: 0.9rem;
                overflow: hidden;
                box-shadow: 0 14px 34px rgba(5, 10, 20, 0.42);
            }

            .hero::before {
                content: "";
                position: absolute;
                inset: 0;
                padding: 1.25px;
                border-radius: 24px;
                background:
                    linear-gradient(
                        90deg,
                        transparent 0%,
                        rgba(191, 238, 255, 0.95) 16%,
                        rgba(56, 189, 248, 0.66) 24%,
                        transparent 40%
                    ),
                    linear-gradient(
                        -90deg,
                        transparent 0%,
                        rgba(191, 238, 255, 0.85) 14%,
                        rgba(34, 211, 238, 0.58) 22%,
                        transparent 38%
                    ),
                    linear-gradient(
                        90deg,
                        rgba(34, 211, 238, 0.12) 0%,
                        rgba(56, 189, 248, 0.22) 50%,
                        rgba(34, 211, 238, 0.12) 100%
                    );
                background-size: 220% 100%, 220% 100%, 100% 100%;
                animation: heroDualBeam 2.1s linear infinite;
                -webkit-mask:
                    linear-gradient(#000 0 0) content-box,
                    linear-gradient(#000 0 0);
                -webkit-mask-composite: xor;
                mask:
                    linear-gradient(#000 0 0) content-box,
                    linear-gradient(#000 0 0);
                mask-composite: exclude;
                filter: drop-shadow(0 0 8px rgba(125, 241, 255, 0.42));
                z-index: 0;
            }

            .hero::after {
                content: "";
                position: absolute;
                inset: 1px;
                border-radius: 22px;
                background: linear-gradient(130deg, rgba(11,26,44,0.9) 0%, rgba(13,34,58,0.86) 55%, rgba(17,44,74,0.84) 100%);
                z-index: 1;
            }

            .hero > * {
                position: relative;
                z-index: 2;
            }

            .hero-tag {
                display: inline-block;
                padding: 0.32rem 0.78rem;
                border-radius: 999px;
                background: linear-gradient(90deg, rgba(34, 211, 238, 0.18) 0%, rgba(56, 189, 248, 0.28) 50%, rgba(34, 211, 238, 0.18) 100%);
                background-size: 220% 100%;
                color: #bff6ff;
                font-size: 0.96rem;
                font-weight: 700;
                letter-spacing: 0.04em;
                margin-bottom: 0.45rem;
                position: relative;
                overflow: hidden;
                border: 1px solid rgba(125, 241, 255, 0.35);
                text-shadow: 0 0 8px rgba(125, 241, 255, 0.45);
                box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.18), 0 0 14px rgba(56, 189, 248, 0.22);
                animation: heroTagGlow 2.4s ease-in-out infinite, heroTagFlow 3.2s linear infinite;
            }

            .hero-tag::after {
                content: "";
                position: absolute;
                top: -20%;
                left: -30%;
                width: 26%;
                height: 140%;
                background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.9) 50%, transparent 100%);
                filter: blur(0.4px);
                transform: skewX(-18deg);
                animation: heroTagSweep 2.8s linear infinite;
            }

            .hero-sub {
                color: var(--text-soft);
                margin-top: 0.35rem;
                text-align: center;
                width: 100%;
            }

            .nf-icon {
                font-family: 'NerdFontSymbolsWeb', "JetBrainsMono Nerd Font", "JetBrainsMono Nerd Font Mono", "Symbols Nerd Font Mono", "Nerd Font Symbols", sans-serif;
                font-weight: 400;
                margin-right: 0.35rem;
                display: inline-block;
                vertical-align: baseline;
                line-height: 1;
            }

            .hero-title {
                margin: 0;
                text-align: center;
                width: 100%;
                position: relative;
                display: inline-block;
                font-weight: 700;
                letter-spacing: 0.01em;
                color: #dff4ff;
                text-shadow: 0 0 14px rgba(56, 189, 248, 0.22);
            }

            .hero-title .title-text {
                display: inline-block;
                position: relative;
                background: linear-gradient(
                    100deg,
                    #f8fdff 0%,
                    #d6f4ff 22%,
                    #8fe7ff 48%,
                    #d8f6ff 72%,
                    #ffffff 100%
                );
                background-size: 220% 100%;
                -webkit-background-clip: text;
                background-clip: text;
                -webkit-text-fill-color: transparent;
                color: transparent;
                filter: drop-shadow(0 0 8px rgba(125, 241, 255, 0.28));
                animation: heroTitleFlow 5.8s linear infinite, heroTitleGlow 3.1s ease-in-out infinite;
            }

            .stTextArea label p {
                color: #e7f3ff !important;
                font-weight: 600 !important;
            }

            .stTextArea [data-baseweb="textarea"] {
                border: 1px solid rgba(103, 232, 249, 0.28) !important;
                border-radius: 12px !important;
                background: rgba(10, 28, 47, 0.76) !important;
                box-shadow: none !important;
                overflow: hidden !important;
            }

            .stTextArea [data-baseweb="textarea"] > textarea {
                border: none !important;
                background: transparent !important;
                color: #e5f2ff !important;
                -webkit-text-fill-color: #e5f2ff !important;
                box-shadow: none !important;
                border-radius: 0 !important;
                caret-color: #ffffff !important;
                font-size: 1.02rem !important;
                font-weight: 500 !important;
            }

            .stTextArea textarea,
            [data-testid="stTextArea"] textarea {
                color: #e5f2ff !important;
                -webkit-text-fill-color: #e5f2ff !important;
                opacity: 1 !important;
                caret-color: #ffffff !important;
            }

            .stTextArea [data-baseweb="textarea"] > textarea::placeholder {
                color: #b7cce6 !important;
                opacity: 0.95 !important;
            }

            [data-testid="stTextArea"] [data-testid="InputInstructions"] {
                color: #dff4ff !important;
                background: rgba(56, 189, 248, 0.22);
                border: 1px solid rgba(125, 241, 255, 0.5);
                border-radius: 999px;
                padding: 0.15rem 0.55rem;
                font-weight: 700;
                font-size: 0.74rem;
                letter-spacing: 0.01em;
            }

            [data-testid="stTextArea"],
            [data-testid="stTextArea"] > div,
            [data-testid="stTextArea"] > div > div {
                background: transparent !important;
                border: none !important;
            }

            [data-testid="stTextArea"] [data-baseweb="base-input"] {
                background: rgba(10, 28, 47, 0.76) !important;
                border-radius: 12px !important;
                overflow: hidden !important;
            }

            .stTextArea [data-baseweb="textarea"]:hover {
                border-color: rgba(125, 241, 255, 0.46) !important;
            }

            .stTextArea [data-baseweb="textarea"]:focus-within {
                border-color: rgba(125, 241, 255, 0.65) !important;
                box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.25) !important;
                outline: none !important;
            }

            div.stButton > button {
                border-radius: 12px;
                border: 1px solid rgba(186, 244, 255, 0.6) !important;
                background: linear-gradient(135deg, #22d3ee 0%, #0284c7 100%) !important;
                color: #fff;
                font-weight: 800;
                letter-spacing: 0.01em;
                text-shadow: 0 1px 1px rgba(0, 0, 0, 0.35);
                box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.2), 0 16px 34px rgba(2, 49, 78, 0.62) !important;
                min-height: 64px !important;
                padding: 1.02rem 1.35rem !important;
                font-size: 1.62rem !important;
                line-height: 1.15 !important;
            }

            div.stButton > button p,
            div.stButton > button span {
                font-size: 1.62rem !important;
                font-weight: 800 !important;
                line-height: 1.1 !important;
                margin: 0 !important;
            }

            div.stButton > button:hover {
                transform: translateY(-1px);
                filter: brightness(1.08);
            }

            [data-testid="stMetric"] {
                background: var(--box-bg);
                border: 1.2px solid var(--box-border);
                border-radius: 14px;
                padding: 0.5rem 0.7rem;
                box-shadow: var(--box-shadow);
            }

            [data-testid="stExpander"],
            [data-testid="stAlert"] {
                background: var(--box-bg);
                border: 1.2px solid var(--box-border);
                border-radius: 14px;
                box-shadow: var(--box-shadow);
            }

            [data-testid="stExpander"] summary {
                display: flex;
                align-items: center;
                padding: 0.42rem 0.55rem 0.42rem 0.95rem;
                min-height: 44px;
            }

            [data-testid="stExpander"] summary p {
                font-size: 1.18rem !important;
                font-weight: 700 !important;
                color: #f0f8ff !important;
                letter-spacing: 0.01em;
                line-height: 1.25 !important;
                margin: 0 !important;
                padding-left: 0.1rem;
            }

            [data-testid="stExpander"] summary svg {
                margin-top: 0 !important;
            }

            [data-testid="stMetricLabel"] p {
                color: #b9d3f0 !important;
                font-weight: 600 !important;
            }

            [data-testid="stMetricValue"] {
                color: #f0f8ff !important;
                font-weight: 700 !important;
            }

            /* Animated pipeline status box */
            [data-testid="stSpinner"] {
                position: relative;
                background: linear-gradient(130deg, rgba(13, 35, 59, 0.86) 0%, rgba(11, 30, 50, 0.86) 100%);
                border: 1px solid rgba(103, 232, 249, 0.28);
                border-radius: 14px;
                padding: 0.75rem 0.9rem;
                overflow: hidden;
                box-shadow: 0 10px 24px rgba(2, 16, 31, 0.45);
                animation: pulseStatus 1.6s ease-in-out infinite;
            }

            [data-testid="stSpinner"]::before {
                content: "";
                position: absolute;
                top: 0;
                left: -35%;
                width: 35%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(125, 241, 255, 0.25), transparent);
                animation: shimmer 1.8s linear infinite;
            }

            [data-testid="stSpinner"] p {
                color: #e9f8ff !important;
                font-weight: 600 !important;
                letter-spacing: 0.01em;
            }

            [data-testid="stSpinner"] svg {
                stroke: #67e8f9 !important;
                filter: drop-shadow(0 0 6px rgba(103, 232, 249, 0.45));
            }

            .success-banner {
                position: relative;
                overflow: hidden;
                background: linear-gradient(145deg, rgba(8, 54, 45, 0.94) 0%, rgba(13, 87, 75, 0.9) 100%);
                border: 1.2px solid rgba(110, 231, 183, 0.62);
                color: #ecfff8;
                border-radius: 14px;
                padding: 0.95rem 1.1rem;
                font-weight: 700;
                font-size: 1.08rem;
                letter-spacing: 0.01em;
                box-shadow: var(--box-shadow);
                margin-bottom: 0.45rem;
                animation: popIn 360ms ease-out;
            }

            .success-banner::before {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(100deg, transparent 0%, rgba(255, 255, 255, 0.16) 45%, transparent 70%);
                transform: translateX(-120%);
                animation: shimmerSuccess 2.2s ease-in-out 1;
            }

            .success-banner strong {
                color: #b7f7dc;
            }

            .overall-fail-banner {
                background: linear-gradient(145deg, rgba(63, 18, 21, 0.92) 0%, rgba(94, 26, 31, 0.88) 100%);
                border: 1.2px solid rgba(248, 113, 113, 0.58);
                border-radius: 12px;
                color: #ffe9e9;
                padding: 0.78rem 0.95rem;
                font-weight: 700;
                box-shadow: var(--box-shadow);
                margin-bottom: 0.45rem;
            }

            .overall-pass-banner {
                background: linear-gradient(145deg, rgba(8, 54, 45, 0.92) 0%, rgba(13, 87, 75, 0.88) 100%);
                border: 1.2px solid rgba(110, 231, 183, 0.62);
                border-radius: 12px;
                color: #e8fff7;
                padding: 0.78rem 0.95rem;
                font-weight: 700;
                box-shadow: var(--box-shadow);
                margin-bottom: 0.45rem;
            }

            .evidence-zero-banner {
                background: linear-gradient(145deg, rgba(73, 43, 12, 0.9) 0%, rgba(102, 58, 16, 0.86) 100%);
                border: 1.2px solid rgba(251, 191, 36, 0.62);
                border-radius: 12px;
                color: #fff4d6;
                padding: 0.72rem 0.92rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
                box-shadow: var(--box-shadow);
            }

            .claim-pass-banner {
                background: linear-gradient(145deg, rgba(8, 54, 45, 0.92) 0%, rgba(13, 87, 75, 0.88) 100%);
                border: 1.2px solid rgba(110, 231, 183, 0.6);
                color: #e9fff8;
                border-radius: 11px;
                padding: 0.66rem 0.84rem;
                font-weight: 700;
                margin-bottom: 0.45rem;
                box-shadow: var(--box-shadow);
            }

            .claim-fail-banner {
                background: linear-gradient(145deg, rgba(63, 18, 21, 0.92) 0%, rgba(94, 26, 31, 0.88) 100%);
                border: 1.2px solid rgba(248, 113, 113, 0.58);
                color: #ffe9e9;
                border-radius: 11px;
                padding: 0.66rem 0.84rem;
                font-weight: 700;
                margin-bottom: 0.45rem;
                box-shadow: var(--box-shadow);
            }

            .evidence-banner {
                background: linear-gradient(145deg, rgba(10, 31, 53, 0.9) 0%, rgba(12, 42, 70, 0.86) 100%);
                border: 1.2px solid rgba(125, 211, 252, 0.45);
                border-radius: 11px;
                color: #e7f4ff;
                padding: 0.62rem 0.84rem;
                font-weight: 700;
                margin: 0.35rem 0;
                box-shadow: var(--box-shadow);
            }

            .evidence-missing-banner {
                background: linear-gradient(145deg, rgba(73, 43, 12, 0.9) 0%, rgba(102, 58, 16, 0.86) 100%);
                border: 1.2px solid rgba(251, 191, 36, 0.58);
                border-radius: 11px;
                color: #fff4d6;
                padding: 0.62rem 0.84rem;
                font-weight: 700;
                margin: 0.35rem 0;
                box-shadow: var(--box-shadow);
            }

            .input-warning-banner {
                background: linear-gradient(145deg, rgba(120, 53, 15, 0.92) 0%, rgba(146, 64, 14, 0.9) 100%);
                border: 1.2px solid rgba(251, 191, 36, 0.72);
                border-radius: 12px;
                color: #fff7e6;
                padding: 0.78rem 0.95rem;
                font-weight: 700;
                margin: 0.45rem 0 0.65rem;
                box-shadow: var(--box-shadow);
            }

            .count-strip {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin: 0.55rem 0 0.4rem;
            }

            .count-chip {
                display: inline-flex;
                align-items: center;
                gap: 0.38rem;
                padding: 0.4rem 0.7rem;
                border-radius: 999px;
                font-weight: 700;
                border: 1.2px solid transparent;
                box-shadow: 0 6px 14px rgba(4, 16, 30, 0.35);
            }

            .count-chip.true {
                background: linear-gradient(145deg, rgba(8, 54, 45, 0.9) 0%, rgba(13, 87, 75, 0.86) 100%);
                border-color: rgba(110, 231, 183, 0.6);
                color: #e8fff7;
            }

            .count-chip.false {
                background: linear-gradient(145deg, rgba(63, 18, 21, 0.9) 0%, rgba(94, 26, 31, 0.86) 100%);
                border-color: rgba(248, 113, 113, 0.58);
                color: #ffe9e9;
            }

            .count-chip.nei {
                background: linear-gradient(145deg, rgba(73, 43, 12, 0.9) 0%, rgba(102, 58, 16, 0.86) 100%);
                border-color: rgba(251, 191, 36, 0.62);
                color: #fff4d6;
            }

            .pipeline-wrap {
                position: relative;
                background: var(--box-bg);
                border: 1.2px solid var(--box-border);
                border-radius: 16px;
                padding: 0.95rem 1rem 0.8rem;
                box-shadow: var(--box-shadow);
                margin-bottom: 0.55rem;
            }

            .pipeline-track {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 0;
                margin-bottom: 0.5rem;
            }

            .p-step {
                position: relative;
                flex: 1;
                text-align: center;
                min-width: 0;
            }

            .p-step:not(:last-child)::after {
                content: "";
                position: absolute;
                left: 50%;
                top: 17px;
                width: 100%;
                height: 4px;
                border-radius: 999px;
                background: rgba(153, 175, 197, 0.32);
            }

            .p-step.done:not(:last-child)::after {
                background: linear-gradient(90deg, #22d3ee 0%, #38bdf8 100%);
                background-size: 220% 100%;
                animation: doneFlow 1.7s linear infinite;
            }

            .p-step.active:not(:last-child)::after {
                background: rgba(129, 210, 255, 0.5);
                overflow: hidden;
            }

            .p-step.active:not(:last-child)::before {
                content: "";
                position: absolute;
                left: 50%;
                top: 14px;
                width: 100%;
                height: 10px;
                background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.75) 45%, transparent 75%);
                animation: flowShine 1.2s linear infinite;
                z-index: 1;
            }

            .p-dot {
                width: 36px;
                height: 36px;
                border-radius: 999px;
                margin: 0 auto 6px;
                display: grid;
                place-items: center;
                font-weight: 700;
                font-family: 'Space Grotesk', sans-serif;
                color: #c4d2df;
                background: rgba(147, 163, 184, 0.34);
                border: 1px solid rgba(196, 208, 221, 0.36);
                position: relative;
                z-index: 2;
                transition: all 0.25s ease;
            }

            .p-step.done .p-dot {
                color: #f5fdff;
                background: linear-gradient(145deg, #22d3ee 0%, #0284c7 100%);
                border-color: rgba(168, 243, 255, 0.6);
                box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.15);
            }

            .p-step.active .p-dot {
                color: #f5fdff;
                background: linear-gradient(145deg, #38bdf8 0%, #2563eb 100%);
                border-color: rgba(191, 238, 255, 0.72);
                box-shadow: 0 0 0 6px rgba(56, 189, 248, 0.2), 0 0 18px rgba(56, 189, 248, 0.45);
                animation: pulseDot 1.2s ease-in-out infinite;
            }

            .p-label {
                font-size: 0.76rem;
                font-weight: 600;
                color: #92a8be;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }

            .p-step.done .p-label,
            .p-step.active .p-label {
                color: #d9edff;
            }

            .pipeline-phase {
                margin-top: 0.2rem;
                text-align: center;
                color: #dff3ff;
                font-weight: 600;
            }

            @keyframes shimmer {
                from { left: -35%; }
                to { left: 110%; }
            }

            @keyframes pulseStatus {
                0% { border-color: rgba(103, 232, 249, 0.22); }
                50% { border-color: rgba(125, 241, 255, 0.5); }
                100% { border-color: rgba(103, 232, 249, 0.22); }
            }

            @keyframes popIn {
                from { opacity: 0; transform: translateY(4px) scale(0.99); }
                to { opacity: 1; transform: translateY(0) scale(1); }
            }

            @keyframes flowShine {
                from { transform: translateX(-110%); }
                to { transform: translateX(100%); }
            }

            @keyframes pulseDot {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }

            @keyframes shimmerSuccess {
                from { transform: translateX(-120%); }
                to { transform: translateX(120%); }
            }

            @keyframes dividerScan {
                from { transform: translateX(0); }
                to { transform: translateX(430%); }
            }

            @keyframes doneFlow {
                from { background-position: 220% 0; }
                to { background-position: -120% 0; }
            }

            @keyframes resultDividerFlow {
                from { background-position: 240% 0; }
                to { background-position: -140% 0; }
            }

            @keyframes dividerBeam {
                from { transform: translateX(0); }
                to { transform: translateX(520%); }
            }

            @keyframes techDrift {
                0% { transform: translate3d(0, 0, 0) rotate(-2deg); }
                50% { transform: translate3d(calc(var(--dx, 160px) * 0.55), calc(var(--dy, 140px) * 0.55), 0) rotate(0.8deg); }
                100% { transform: translate3d(var(--dx, 160px), var(--dy, 140px), 0) rotate(2deg); }
            }

            @keyframes heroDualBeam {
                0% {
                    background-position: 220% 0, -160% 0, 0 0;
                    opacity: 0.9;
                }
                50% {
                    background-position: 40% 0, 20% 0, 0 0;
                    opacity: 1;
                }
                100% {
                    background-position: -160% 0, 220% 0, 0 0;
                    opacity: 0.9;
                }
            }

            @keyframes heroTagFlow {
                from { background-position: 220% 0; }
                to { background-position: -120% 0; }
            }

            @keyframes heroTagGlow {
                0% {
                    text-shadow: 0 0 6px rgba(125, 241, 255, 0.35);
                    box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.14), 0 0 10px rgba(56, 189, 248, 0.16);
                }
                50% {
                    text-shadow: 0 0 12px rgba(191, 238, 255, 0.72);
                    box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.24), 0 0 20px rgba(56, 189, 248, 0.34);
                }
                100% {
                    text-shadow: 0 0 6px rgba(125, 241, 255, 0.35);
                    box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.14), 0 0 10px rgba(56, 189, 248, 0.16);
                }
            }

            @keyframes heroTagSweep {
                from { transform: translateX(0) skewX(-18deg); }
                to { transform: translateX(560%) skewX(-18deg); }
            }

            @keyframes heroTitleFlow {
                from { background-position: 220% 0; }
                to { background-position: -120% 0; }
            }

            @keyframes heroTitleGlow {
                0% {
                    filter: drop-shadow(0 0 6px rgba(125, 241, 255, 0.2));
                }
                50% {
                    filter: drop-shadow(0 0 13px rgba(191, 238, 255, 0.45));
                }
                100% {
                    filter: drop-shadow(0 0 6px rgba(125, 241, 255, 0.2));
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_animated_tech_background() -> None:
    st.markdown(
        """
        <div class="tech-bg" aria-hidden="true">
            <span class="tech-badge b1"><img class="tech-logo" src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" alt="Python logo"></span>
            <span class="tech-badge b2"><img class="tech-logo" src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/streamlit/streamlit-original.svg" alt="Streamlit logo"></span>
            <span class="tech-badge b3"><img class="tech-logo logo-light" src="https://cdn.jsdelivr.net/npm/simple-icons/icons/langchain.svg" alt="LangChain logo"></span>
            <span class="tech-badge b4"><img class="tech-logo" src="data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%230b4a6f'/%3E%3Cpath d='M16 22h14v8H24v12h-8zM34 34h14v8H34zM40 22h8v8h-8zM24 38h8v8h-8z' fill='%2367e8f9'/%3E%3C/svg%3E" alt="LangGraph logo"></span>
            <span class="tech-badge b5"><img class="tech-logo" src="data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%232c1b63'/%3E%3Ccircle cx='22' cy='26' r='7' fill='%239b8cff'/%3E%3Ccircle cx='42' cy='22' r='6' fill='%23bfa7ff'/%3E%3Ccircle cx='40' cy='42' r='7' fill='%23826dff'/%3E%3Cpath d='M22 26l20-4M42 22l-2 20M22 26l18 16' stroke='white' stroke-width='2.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E" alt="Qdrant logo"></span>
            <span class="tech-badge b6"><img class="tech-logo logo-wide" src="data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%230e7490'/%3E%3Cpath d='M14 36c8-12 18-18 30-18-5 3-8 6-10 10 4 1 8 4 12 8-9-2-17-1-24 4z' fill='white' opacity='0.95'/%3E%3Ccircle cx='42' cy='24' r='3' fill='%2367e8f9'/%3E%3C/svg%3E" alt="DeepSeek logo"></span>
            <span class="tech-badge b7"><img class="tech-logo logo-wide" src="data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%231e3a8a'/%3E%3Ccircle cx='22' cy='24' r='8' fill='%2360a5fa'/%3E%3Ccircle cx='40' cy='24' r='8' fill='%2393c5fd'/%3E%3Crect x='18' y='36' width='28' height='10' rx='5' fill='white' opacity='0.95'/%3E%3C/svg%3E" alt="Serper logo"></span>
            <span class="tech-badge b8"><img class="tech-logo" src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg" alt="Docker logo"></span>
            <span class="tech-badge b9"><img class="tech-logo" src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/pandas/pandas-original.svg" alt="Pandas logo"></span>
            <span class="tech-badge b10"><img class="tech-logo" src="data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' x2='1'%3E%3Cstop offset='0' stop-color='%2306b6d4'/%3E%3Cstop offset='1' stop-color='%231d4ed8'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='64' height='64' rx='12' fill='url(%23g)'/%3E%3Ctext x='32' y='39' text-anchor='middle' font-family='Arial,sans-serif' font-size='15' font-weight='700' fill='white'%3ERAG%3C/text%3E%3C/svg%3E" alt="RAG logo"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _animated_divider() -> None:
    st.markdown('<div class="nf-divider"></div>', unsafe_allow_html=True)


def _render_pipeline_progress(step: int, phase_text: str, slot) -> None:
    steps = ["Decompose", "Checkworthy", "Retrieve", "Verify"]
    blocks = []
    for idx, label in enumerate(steps, start=1):
        if idx < step:
            cls = "done"
        elif idx == step:
            cls = "active"
        else:
            cls = "pending"
        blocks.append(
            f'<div class="p-step {cls}"><div class="p-dot">{idx}</div><div class="p-label">{label}</div></div>'
        )

    slot.markdown(
        (
            '<div class="pipeline-wrap">'
            '<div class="pipeline-track">'
            f"{''.join(blocks)}"
            '</div>'
            f'<div class="pipeline-phase">{phase_text}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def _run_pipeline_with_live_status(initial_state: dict) -> dict:
    state = dict(initial_state)

    progress_slot = st.empty()

    _render_pipeline_progress(1, "Đang chạy Phase 1/4: Decompose", progress_slot)
    state.update(decompose_node(state))

    _render_pipeline_progress(2, "Đang chạy Phase 2/4: Checkworthy", progress_slot)
    state.update(checkworthy_node(state))

    _render_pipeline_progress(3, "Đang chạy Phase 3/4: Retrieve", progress_slot)
    state.update(retrieve_node(state))
    evidence_count = sum(len(v) for v in state.get("evidence", {}).values())

    all_empty = all(not ev for ev in state.get("evidence", {}).values()) if state.get("evidence") else True
    if all_empty and state.get("retry_count", 0) < 1:
        _render_pipeline_progress(3, "Đang retry Phase 3/4: Retrieve", progress_slot)
        state.update(retrieve_node(state))
        evidence_count = sum(len(v) for v in state.get("evidence", {}).values())

    _render_pipeline_progress(4, "Đang chạy Phase 4/4: Verify", progress_slot)
    state.update(verify_node(state))

    _render_pipeline_progress(4, "Pipeline hoàn tất", progress_slot)

    return state

st.set_page_config(page_title="NeuralFact Checker", layout="wide")

_inject_modern_styles()
_render_animated_tech_background()

st.markdown(
    """
    <div class="hero">
        <div class="hero-tag">NEURALFACT TEAM PRODUCTION</div>
        <h1 class="hero-title"><span class="title-text">Hệ Thống Kiểm Chứng Tin Giả</span></h1>
    </div>
    """,
    unsafe_allow_html=True,
)

user_input = st.text_area("Nhập mệnh đề cần kiểm chứng:", height=130)

left_col, center_col, right_col = st.columns([1, 2, 1])
with center_col:
    run_check = st.button("Kiểm tra ngay", type="primary", use_container_width=True)

if run_check:
    if not user_input.strip():
        st.markdown(f'<div class="input-warning-banner">{ICON_WARN} Vui lòng nhập văn bản!</div>', unsafe_allow_html=True)
    else:
        start_time = time.time()

        initial_state = {
            "input_text": user_input, "claims": [], "checkworthy_claims": [],
            "queries": {}, "evidence": {}, "verdicts": {}, "overall_verdict": {}, "retry_count": 0,
            "prompt_tokens": 0, "completion_tokens": 0
        }

        try:
            final_state = _run_pipeline_with_live_status(initial_state)
                
            latency = round(time.time() - start_time, 2)
            prompt_tokens = final_state.get("prompt_tokens", 0)
            completion_tokens = final_state.get("completion_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens
                
            # Calculate cost based on input and output token prices
            input_cost = (prompt_tokens / 1_000_000) * PRICE_1M_INPUT_TOKENS
            output_cost = (completion_tokens / 1_000_000) * PRICE_1M_OUTPUT_TOKENS
            total_cost = round(input_cost + output_cost, 6)
                
            st.markdown(f'<div class="success-banner">{ICON_CHECK} <strong>Hoàn tất kiểm chứng</strong> - kết quả đã sẵn sàng để bạn phân tích.</div>', unsafe_allow_html=True)
                
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Thời gian (Latency)", f"{latency}s")
            col2.metric("Input Tokens", f"{prompt_tokens}")
            col3.metric("Output Tokens", f"{completion_tokens}")
            col4.metric("Chi phí ước tính", f"${total_cost}")
                
            _animated_divider()
            st.markdown(f"### {ICON_DETAIL} Kết quả chi tiết", unsafe_allow_html=True)

            evidence_total = sum(len(v) for v in final_state.get("evidence", {}).values())
            if evidence_total == 0:
                st.markdown(
                    f'<div class="evidence-zero-banner">{ICON_WARN} Thu thập được 0 bằng chứng. Kết luận có thể thiếu độ tin cậy.</div>',
                    unsafe_allow_html=True,
                )

            overall = final_state.get("overall_verdict", {})
            if overall:
                fact = overall.get("factuality", False)
                summary = overall.get("summary", "")
                counts = overall.get("counts", {})
                st.markdown(f"### {ICON_SUMMARY} Kết luận toàn bộ bản tin", unsafe_allow_html=True)
                if fact is True:
                    st.markdown(f'<div class="overall-pass-banner">{ICON_CHECK} Kết luận tổng: ĐÚNG</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="overall-fail-banner">{ICON_FAIL} Kết luận tổng: SAI</div>', unsafe_allow_html=True)

                if summary:
                    st.markdown(f"**Tóm tắt:** {summary}")
                if isinstance(counts, dict):
                    st.markdown(
                        (
                            '<div class="count-strip">'
                            f'<div class="count-chip true">{ICON_CHECK} Đúng: {counts.get("true", 0)}</div>'
                            f'<div class="count-chip false">{ICON_FAIL} Sai: {counts.get("false", 0)}</div>'
                            f'<div class="count-chip nei">{ICON_WARN} NEI: {counts.get("nei", 0)}</div>'
                            '</div>'
                        ),
                        unsafe_allow_html=True,
                    )
                _animated_divider()
                
            for claim, verdict_data in final_state["verdicts"].items():
                with st.expander(f"Mệnh đề: {claim}", expanded=True):
                    factuality = verdict_data.get("factuality", "NEI")
                    reasoning = verdict_data.get("reasoning", "")
                    error = verdict_data.get("error", "không có")
                    correction = verdict_data.get("correction", "không có")
                    
                    # Display verdict with appropriate color
                    if factuality == True or str(factuality).lower() == "true":
                        st.markdown(f'<div class="claim-pass-banner">{ICON_CHECK} Kết luận: ĐÚNG (Supported)</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="claim-fail-banner">{ICON_FAIL} Kết luận: SAI / KHÔNG ĐỦ CĂN CỨ</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"**Lý do (Reasoning):** {reasoning}")
                    
                    # Show error and correction if exists
                    if error != "không có" and error != "none":
                        st.markdown(f"**Lỗi phát hiện:** {error}")
                    if correction != "không có" and correction != "none":
                        st.markdown(f"**Sửa chữa đề xuất:** {correction}")
                    
                    # Display evidence sources
                    evidences = final_state["evidence"].get(claim, [])
                    if evidences:
                        st.markdown(
                            f'<div class="evidence-banner">{ICON_EVID} Bằng chứng ({len(evidences)} nguồn)</div>',
                            unsafe_allow_html=True,
                        )
                        for i, ev in enumerate(evidences[:3], 1):  # Show top 3
                            with st.container():
                                st.caption(f"Nguồn {i}:")
                                st.text(_display_evidence_text(ev))
                    else:
                        st.markdown(
                            f'<div class="evidence-missing-banner">{ICON_WARN} Bằng chứng: Không tìm thấy dữ liệu.</div>',
                            unsafe_allow_html=True,
                        )
                    
                    # Show queries used
                    queries = final_state["queries"].get(claim, [])
                    if queries:
                        st.caption(f"*Câu hỏi kiểm tra: {', '.join(queries[:3])}*")

        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {e}")
