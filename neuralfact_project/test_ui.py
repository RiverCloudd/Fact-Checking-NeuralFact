"""
UI Test App - Test từng component với Streamlit
Chạy: streamlit run test_ui.py
"""
import streamlit as st
import json
import time


def _display_evidence_text(ev) -> str:
    if isinstance(ev, dict):
        return str(ev.get("text", "")).strip()
    return str(ev or "").strip()


def _inject_modern_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

            :root {
                --bg-a: #081425;
                --bg-b: #0a1d36;
                --bg-c: #102844;
                --card: rgba(12, 29, 49, 0.82);
                --text-main: #d9e9ff;
                --text-soft: #9bb4d3;
                --brand: #22d3ee;
                --brand-deep: #06b6d4;
                --ring: rgba(34, 211, 238, 0.28);
            }

            .stApp {
                background:
                    radial-gradient(circle at 10% 10%, rgba(45, 212, 191, 0.12) 0%, transparent 35%),
                    radial-gradient(circle at 92% 0%, rgba(56, 189, 248, 0.15) 0%, transparent 38%),
                    linear-gradient(130deg, var(--bg-a) 0%, var(--bg-b) 52%, var(--bg-c) 100%);
                color: var(--text-main);
                font-family: 'IBM Plex Sans', sans-serif;
            }

            /* Remove Streamlit top white header/deploy strip */
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

            h1, h2, h3, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
                font-family: 'Space Grotesk', sans-serif;
                letter-spacing: -0.01em;
            }

            .block-container {
                max-width: 1180px;
                padding-top: 1.35rem;
                padding-bottom: 2.2rem;
            }

            .hero {
                background: linear-gradient(130deg, rgba(11,26,44,0.9) 0%, rgba(13,34,58,0.86) 55%, rgba(17,44,74,0.84) 100%);
                border: 1px solid var(--ring);
                border-radius: 24px;
                padding: 1.1rem 1.2rem;
                margin-bottom: 0.9rem;
                box-shadow: 0 14px 34px rgba(5, 10, 20, 0.42);
                animation: lift 520ms ease-out;
            }

            .hero-tag {
                display: inline-block;
                padding: 0.2rem 0.6rem;
                border-radius: 999px;
                background: rgba(34, 211, 238, 0.16);
                color: #67e8f9;
                font-size: 0.78rem;
                font-weight: 600;
                margin-bottom: 0.45rem;
            }

            .hero-sub {
                color: var(--text-soft);
                margin-top: 0.35rem;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0b1c31 0%, #0f2744 54%, #123259 100%);
                border-right: 1px solid rgba(103, 232, 249, 0.18);
            }

            [data-testid="stSidebar"] > div {
                background: linear-gradient(180deg, #0b1c31 0%, #0f2744 54%, #123259 100%);
            }

            [data-testid="stSidebar"] * {
                color: #d7e8ff;
            }

            [data-testid="stSidebar"] .stAlert {
                background: rgba(15, 39, 68, 0.88);
                border: 1px solid rgba(103, 232, 249, 0.2);
                border-radius: 12px;
            }

            [data-testid="stSidebar"] [data-baseweb="select"] > div,
            [data-testid="stSidebar"] .stTextInput input,
            [data-testid="stSidebar"] .stNumberInput input,
            [data-testid="stSidebar"] textarea {
                background: rgba(9, 25, 44, 0.8) !important;
                color: #dff1ff !important;
                border: 1px solid rgba(103, 232, 249, 0.24) !important;
                border-radius: 10px !important;
                box-shadow: none !important;
            }

            /* Keep all main widgets in the same tech tone as verification text areas */
            .stSelectbox [data-baseweb="select"] > div,
            .stTextInput input,
            .stNumberInput input {
                background: rgba(10, 28, 47, 0.76) !important;
                color: #e5f2ff !important;
                border: 1px solid rgba(103, 232, 249, 0.28) !important;
                border-radius: 12px !important;
                box-shadow: none !important;
            }

            /* Increase field label contrast on dark background */
            .stTextArea label p,
            .stTextInput label p,
            .stSelectbox label p,
            .stNumberInput label p {
                color: #e7f3ff !important;
                font-weight: 600 !important;
            }

            /* Fix textarea border glitches by styling container and inner textarea separately */
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
                box-shadow: none !important;
                border-radius: 0 !important;
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

            .stSelectbox [data-baseweb="select"] > div:hover,
            .stTextInput input:hover,
            .stNumberInput input:hover,
            .stTextArea [data-baseweb="textarea"]:hover {
                border-color: rgba(125, 241, 255, 0.46) !important;
            }

            .stSelectbox [data-baseweb="select"] > div:focus-within,
            .stTextInput input:focus,
            .stNumberInput input:focus,
            .stTextArea [data-baseweb="textarea"]:focus-within {
                border-color: rgba(125, 241, 255, 0.65) !important;
                box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.25) !important;
                outline: none !important;
            }

            .stSelectbox svg,
            .stTextInput svg,
            .stNumberInput svg {
                fill: #9fd8ff !important;
            }

            .stCheckbox label,
            .stCheckbox label p,
            .stCheckbox span {
                color: #eaf5ff !important;
                font-weight: 600 !important;
            }

            .stCheckbox input[type="checkbox"] {
                accent-color: #22d3ee;
            }

            [data-testid="stSidebar"] hr {
                border-color: rgba(103, 232, 249, 0.2);
            }

            .stat-card {
                background: var(--card);
                border: 1px solid rgba(103, 232, 249, 0.22);
                border-radius: 16px;
                padding: 0.7rem 0.85rem;
                box-shadow: 0 8px 20px rgba(4, 9, 17, 0.42);
                margin-bottom: 0.45rem;
            }

            .stat-label {
                color: #9db7d8;
                font-size: 0.82rem;
            }

            .stat-value {
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.2rem;
                font-weight: 700;
                margin-top: 0.1rem;
                color: #e4f1ff;
            }

            /* Make Streamlit metric blocks in tabs clearer on dark background */
            [data-testid="stMetric"] {
                background: rgba(9, 25, 44, 0.72);
                border: 1px solid rgba(103, 232, 249, 0.24);
                border-radius: 14px;
                padding: 0.5rem 0.7rem;
            }

            [data-testid="stMetricLabel"] p {
                color: #b9d3f0 !important;
                font-weight: 600 !important;
            }

            [data-testid="stMetricValue"] {
                color: #f0f8ff !important;
                font-weight: 700 !important;
            }

            [data-testid="stMetricDelta"] {
                color: #93e5ff !important;
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.4rem;
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 999px;
                background: rgba(13, 35, 59, 0.84);
                color: #c6dcf7;
                border: 1px solid rgba(103, 232, 249, 0.14);
                padding: 0.45rem 0.8rem;
            }

            .stTabs [aria-selected="true"] {
                background: rgba(34, 211, 238, 0.2) !important;
                border-color: rgba(103, 232, 249, 0.5) !important;
                color: #effbff !important;
            }

            div.stButton > button {
                border-radius: 12px;
                border: 0;
                background: linear-gradient(135deg, #06b6d4 0%, #0ea5e9 100%);
                color: #fff;
                font-weight: 700;
                letter-spacing: 0.01em;
                text-shadow: 0 1px 1px rgba(0, 0, 0, 0.35);
                box-shadow: 0 12px 26px rgba(8, 47, 73, 0.52);
                border: 1px solid rgba(147, 235, 255, 0.4);
            }

            div.stButton > button:hover {
                transform: translateY(-1px);
                filter: brightness(1.08);
                box-shadow: 0 14px 30px rgba(8, 47, 73, 0.6);
            }

            div.stButton > button[data-testid="baseButton-primary"],
            div.stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #22d3ee 0%, #0284c7 100%) !important;
                border: 1px solid rgba(186, 244, 255, 0.6) !important;
                box-shadow: 0 0 0 1px rgba(125, 241, 255, 0.2), 0 16px 34px rgba(2, 49, 78, 0.62) !important;
            }

            [data-testid="stTextArea"] textarea {
                border-radius: 0 !important;
                border: none !important;
                background: transparent !important;
                color: #e5f2ff !important;
            }

            @keyframes lift {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @media (max-width: 768px) {
                .block-container {
                    padding-left: 0.9rem;
                    padding-right: 0.9rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_stat_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.set_page_config(page_title="NeuralFact - Component Testing", layout="wide")

_inject_modern_styles()

st.markdown(
    """
    <div class="hero">
        <div class="hero-tag">NEURALFACT LAB</div>
        <h1 style="margin:0;">Component Testing Console</h1>
        <p class="hero-sub">Theo dõi từng node trong pipeline kiểm chứng với giao diện gọn, trực quan và hiện đại.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if 'state' not in st.session_state:
    st.session_state.state = {
        "input_text": "",
        "claims": [],
        "checkworthy_claims": [],
        "queries": {},
        "evidence": {},
        "verdicts": {},
        "retry_count": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0
    }

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Check dependencies
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from config.prompts_config import prompt_config
        from core.config import get_llm, PRICE_1M_INPUT_TOKENS, PRICE_1M_OUTPUT_TOKENS
        st.success("✅ Config loaded")
    except Exception as e:
        st.error(f"❌ Config error: {e}")
        st.stop()
    
    # Check API keys
    import os
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    serper_key = os.getenv("SERPER_API_KEY")
    
    if gemini_key:
        st.success(f"✅ Gemini: {gemini_key[:10]}...")
    else:
        st.error("❌ Gemini API key missing")
    
    if serper_key:
        st.success(f"✅ Serper: {serper_key[:10]}...")
    else:
        st.warning("⚠️ Serper API key missing")
    
    st.divider()
    
    # Current tokens
    _render_stat_card("Input Tokens", str(st.session_state.state['prompt_tokens']))
    _render_stat_card("Output Tokens", str(st.session_state.state['completion_tokens']))
    
    total_tokens = st.session_state.state['prompt_tokens'] + st.session_state.state['completion_tokens']
    if total_tokens > 0:
        input_cost = (st.session_state.state['prompt_tokens'] / 1_000_000) * PRICE_1M_INPUT_TOKENS
        output_cost = (st.session_state.state['completion_tokens'] / 1_000_000) * PRICE_1M_OUTPUT_TOKENS
        total_cost = input_cost + output_cost
        _render_stat_card("Total Cost", f"${total_cost:.6f}")
    
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        reset_clicked = st.button("🔄 Reset State", use_container_width=True)

    if reset_clicked:
        st.session_state.state = {
            "input_text": "",
            "claims": [],
            "checkworthy_claims": [],
            "queries": {},
            "evidence": {},
            "verdicts": {},
            "retry_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
        st.rerun()

# Main content
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Input & Decompose",
    "✔️ Checkworthy",
    "🔍 Retrieval",
    "✅ Verification",
    "📊 Full Pipeline"
])

# ============================================================
# TAB 1: INPUT & DECOMPOSE
# ============================================================
with tab1:
    st.header("📝 Bước 1: Input & Decompose")
    st.markdown("Nhập văn bản và phân tách thành các atomic claims")
    
    # Input
    test_examples = {
        "Ví dụ 1: Đơn giản": "Hà Nội là thủ đô của Việt Nam.",
        "Ví dụ 2: Nhiều claims": "Thành phố Hồ Chí Minh là thành phố lớn nhất Việt Nam với dân số khoảng 9 triệu người. Thành phố được thành lập năm 1698.",
        "Ví dụ 3: Có sai sót": "Obama là tổng thống thứ 44 của Anh. Ông sinh năm 1961 tại Hawaii.",
        "Custom": ""
    }
    
    selected_example = st.selectbox("Chọn ví dụ:", list(test_examples.keys()))
    
    if selected_example == "Custom":
        input_text = st.text_area(
            "Nhập văn bản cần kiểm chứng:",
            value=st.session_state.state['input_text'],
            height=150,
            key="input_text_area"
        )
    else:
        input_text = st.text_area(
            "Nhập văn bản cần kiểm chứng:",
            value=test_examples[selected_example],
            height=150,
            key="input_text_area_example"
        )
    
    st.session_state.state['input_text'] = input_text
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        run_decompose = st.button("▶️ Run Decompose", type="primary", use_container_width=True)
    
    with col2:
        show_prompt = st.checkbox("Hiển thị prompt", key="show_decompose_prompt")
    
    if show_prompt:
        with st.expander("📋 Decompose Prompt Template"):
            st.code(prompt_config.decompose_prompt, language="text")
    
    # Run decompose
    if run_decompose and input_text.strip():
        with st.spinner("Đang phân tách claims..."):
            try:
                from pipeline.nodes import decompose_node
                
                start_time = time.time()
                result = decompose_node(st.session_state.state)
                elapsed = time.time() - start_time
                
                st.session_state.state.update(result)
                
                st.success(f"✅ Hoàn thành trong {elapsed:.2f}s")
                
                # Display results
                st.subheader("📊 Kết quả:")
                st.info(f"Tìm thấy **{len(st.session_state.state['claims'])}** claims")
                
                for i, claim in enumerate(st.session_state.state['claims'], 1):
                    st.markdown(f"{i}. {claim}")
                
                # Token info
                col1, col2, col3 = st.columns(3)
                col1.metric("Input Tokens", st.session_state.state['prompt_tokens'])
                col2.metric("Output Tokens", st.session_state.state['completion_tokens'])
                col3.metric("Latency", f"{elapsed:.2f}s")
                
            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
                import traceback
                with st.expander("Chi tiết lỗi"):
                    st.code(traceback.format_exc())
    
    elif run_decompose:
        st.warning("⚠️ Vui lòng nhập văn bản")
    
    # Display current state
    if st.session_state.state['claims']:
        st.divider()
        st.subheader("📦 Current State")
        with st.expander("Xem state hiện tại"):
            st.json({
                "claims": st.session_state.state['claims'],
                "tokens": {
                    "input": st.session_state.state['prompt_tokens'],
                    "output": st.session_state.state['completion_tokens']
                }
            })

# ============================================================
# TAB 2: CHECKWORTHY
# ============================================================
with tab2:
    st.header("✔️ Bước 2: Checkworthy Filter")
    st.markdown("Lọc các claims đáng kiểm chứng")
    
    if not st.session_state.state['claims']:
        st.warning("⚠️ Chưa có claims. Vui lòng chạy Decompose ở Tab 1 trước.")
    else:
        st.info(f"Có **{len(st.session_state.state['claims'])}** claims cần filter")
        
        with st.expander("📋 Claims hiện tại"):
            for i, claim in enumerate(st.session_state.state['claims'], 1):
                st.markdown(f"{i}. {claim}")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            run_checkworthy = st.button("▶️ Run Checkworthy", type="primary", use_container_width=True)
        
        with col2:
            show_prompt_cw = st.checkbox("Hiển thị prompt", key="show_checkworthy_prompt")
        
        if show_prompt_cw:
            with st.expander("📋 Checkworthy Prompt Template"):
                st.code(prompt_config.checkworthy_prompt, language="text")
        
        if run_checkworthy:
            with st.spinner("Đang filter checkworthy claims..."):
                try:
                    from pipeline.nodes import checkworthy_node
                    
                    start_time = time.time()
                    result = checkworthy_node(st.session_state.state)
                    elapsed = time.time() - start_time
                    
                    st.session_state.state.update(result)
                    
                    st.success(f"✅ Hoàn thành trong {elapsed:.2f}s")
                    
                    # Results
                    st.subheader("📊 Kết quả:")
                    checkworthy_count = len(st.session_state.state['checkworthy_claims'])
                    total_count = len(st.session_state.state['claims'])
                    
                    st.info(f"**{checkworthy_count}/{total_count}** claims đáng kiểm chứng")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**✅ Checkworthy:**")
                        for claim in st.session_state.state['checkworthy_claims']:
                            st.markdown(f"- {claim}")
                    
                    with col2:
                        not_checkworthy = [c for c in st.session_state.state['claims'] 
                                          if c not in st.session_state.state['checkworthy_claims']]
                        if not_checkworthy:
                            st.markdown("**❌ Not Checkworthy:**")
                            for claim in not_checkworthy:
                                st.markdown(f"- {claim}")
                    
                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Input Tokens", st.session_state.state['prompt_tokens'])
                    col2.metric("Output Tokens", st.session_state.state['completion_tokens'])
                    col3.metric("Latency", f"{elapsed:.2f}s")
                    
                except Exception as e:
                    st.error(f"❌ Lỗi: {e}")
                    import traceback
                    with st.expander("Chi tiết lỗi"):
                        st.code(traceback.format_exc())

# ============================================================
# TAB 3: RETRIEVAL
# ============================================================
with tab3:
    st.header("🔍 Bước 3: Evidence Retrieval")
    st.markdown("Thu thập bằng chứng từ Google (và Qdrant nếu bật USE_QDRANT=true)")
    
    if not st.session_state.state['checkworthy_claims']:
        st.warning("⚠️ Chưa có checkworthy claims. Chạy Tab 2 trước.")
    else:
        st.info(f"Có **{len(st.session_state.state['checkworthy_claims'])}** claims cần retrieve")
        
        st.warning("⚠️ **Lưu ý:** Bước này sẽ gọi Serper API (tốn credit)")
        
        run_retrieval = st.button("▶️ Run Retrieval", type="primary", use_container_width=True)
        
        if run_retrieval:
            with st.spinner("Đang thu thập bằng chứng..."):
                try:
                    from pipeline.nodes import retrieve_node
                    
                    start_time = time.time()
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    result = retrieve_node(st.session_state.state)
                    
                    progress_bar.progress(100)
                    elapsed = time.time() - start_time
                    
                    st.session_state.state.update(result)
                    
                    status_text.success(f"✅ Hoàn thành trong {elapsed:.2f}s")
                    
                    # Results
                    st.subheader("📊 Kết quả:")
                    total_evidences = sum(len(e) for e in st.session_state.state['evidence'].values())
                    st.info(f"Thu thập được **{total_evidences}** evidences")
                    
                    for claim, evidences in st.session_state.state['evidence'].items():
                        with st.expander(f"📌 {claim[:80]}... ({len(evidences)} evidences)"):
                            if evidences:
                                for i, ev in enumerate(evidences, 1):  # Show top 5
                                    st.markdown(f"**Nguồn {i}:**")
                                    st.text(_display_evidence_text(ev))
                                    st.divider()
                            else:
                                st.warning("Không tìm thấy evidence")
                    
                    st.metric("Latency", f"{elapsed:.2f}s")
                    
                except Exception as e:
                    st.error(f"❌ Lỗi: {e}")
                    import traceback
                    with st.expander("Chi tiết lỗi"):
                        st.code(traceback.format_exc())

# ============================================================
# TAB 4: VERIFICATION
# ============================================================
with tab4:
    st.header("✅ Bước 4: Verification")
    st.markdown("Kiểm chứng claims với error detection")
    
    if not st.session_state.state['evidence']:
        st.warning("⚠️ Chưa có evidence. Chạy Tab 4 trước.")
    else:
        st.info(f"Có **{len(st.session_state.state['evidence'])}** claims cần verify")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            run_verify = st.button("▶️ Run Verification", type="primary", use_container_width=True)
        
        with col2:
            show_prompt_vf = st.checkbox("Hiển thị prompt", key="show_verify_prompt")
        
        if show_prompt_vf:
            with st.expander("📋 Verification Prompt Template"):
                st.code(prompt_config.verify_prompt, language="text")
        
        if run_verify:
            with st.spinner("Đang kiểm chứng..."):
                try:
                    from pipeline.nodes import verify_node
                    
                    start_time = time.time()
                    result = verify_node(st.session_state.state)
                    elapsed = time.time() - start_time
                    
                    st.session_state.state.update(result)
                    
                    st.success(f"✅ Hoàn thành trong {elapsed:.2f}s")
                    
                    # Results
                    st.subheader("📊 Kết quả:")
                    
                    for claim, verdict in st.session_state.state['verdicts'].items():
                        with st.expander(f"📌 {claim}"):
                            factuality = verdict.get('factuality')
                            
                            if factuality == True or str(factuality).lower() == "true":
                                st.success("✅ **ĐÚNG** (Supported)")
                            else:
                                st.error("❌ **SAI / KHÔNG ĐỦ CĂN CỨ**")
                            
                            st.markdown(f"**Reasoning:** {verdict.get('reasoning', '')}")
                            
                            error = verdict.get('error', 'không có')
                            correction = verdict.get('correction', 'không có')
                            
                            if error != 'không có' and error != 'none':
                                st.markdown(f"**⚠️ Lỗi phát hiện:** {error}")
                            
                            if correction != 'không có' and correction != 'none':
                                st.markdown(f"**💡 Sửa chữa:** {correction}")
                    
                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Input Tokens", st.session_state.state['prompt_tokens'])
                    col2.metric("Output Tokens", st.session_state.state['completion_tokens'])
                    col3.metric("Latency", f"{elapsed:.2f}s")
                    
                except Exception as e:
                    st.error(f"❌ Lỗi: {e}")
                    import traceback
                    with st.expander("Chi tiết lỗi"):
                        st.code(traceback.format_exc())

# ============================================================
# TAB 5: FULL PIPELINE
# ============================================================
with tab5:
    st.header("📊 Full Pipeline Test")
    st.markdown("Chạy toàn bộ pipeline một lần")
    
    # Input
    full_input = st.text_area(
        "Nhập văn bản cần kiểm chứng:",
        value="Obama là tổng thống thứ 44 của Anh. Ông sinh năm 1961 tại Hawaii.",
        height=150,
        key="full_pipeline_input"
    )
    
    run_full = st.button("▶️ Run Full Pipeline", type="primary", use_container_width=True)
    
    if run_full and full_input.strip():
        # Reset state
        st.session_state.state = {
            "input_text": full_input,
            "claims": [],
            "checkworthy_claims": [],
            "queries": {},
            "evidence": {},
            "verdicts": {},
            "retry_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
        
        from pipeline.nodes import (
            decompose_node,
            checkworthy_node,
            retrieve_node,
            verify_node
        )
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Decompose
            status_text.text("1/4 Decompose...")
            result = decompose_node(st.session_state.state)
            st.session_state.state.update(result)
            progress_bar.progress(25)
            
            # Step 2: Checkworthy
            status_text.text("2/4 Checkworthy...")
            result = checkworthy_node(st.session_state.state)
            st.session_state.state.update(result)
            progress_bar.progress(50)
            
            # Step 3: Retrieval
            status_text.text("3/4 Retrieval...")
            result = retrieve_node(st.session_state.state)
            st.session_state.state.update(result)
            progress_bar.progress(75)
            
            # Step 4: Verification
            status_text.text("4/4 Verification...")
            result = verify_node(st.session_state.state)
            st.session_state.state.update(result)
            progress_bar.progress(100)
            
            status_text.success("✅ Pipeline hoàn thành!")
            
            # Display summary
            st.divider()
            st.subheader("📊 Tổng kết")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Claims", len(st.session_state.state['claims']))
            col2.metric("Checkworthy", len(st.session_state.state['checkworthy_claims']))
            col3.metric("Evidences", sum(len(e) for e in st.session_state.state['evidence'].values()))
            
            # Tokens & Cost
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("Input Tokens", st.session_state.state['prompt_tokens'])
            col2.metric("Output Tokens", st.session_state.state['completion_tokens'])
            
            input_cost = (st.session_state.state['prompt_tokens'] / 1_000_000) * PRICE_1M_INPUT_TOKENS
            output_cost = (st.session_state.state['completion_tokens'] / 1_000_000) * PRICE_1M_OUTPUT_TOKENS
            total_cost = input_cost + output_cost
            col3.metric("Total Cost", f"${total_cost:.6f}")
            
            # Results
            st.divider()
            st.subheader("🎯 Kết quả Verification")
            
            for claim, verdict in st.session_state.state['verdicts'].items():
                with st.expander(f"📌 {claim}"):
                    factuality = verdict.get('factuality')
                    
                    if factuality == True or str(factuality).lower() == "true":
                        st.success("✅ **ĐÚNG**")
                    else:
                        st.error("❌ **SAI / KHÔNG ĐỦ CĂN CỨ**")
                    
                    st.markdown(f"**Reasoning:** {verdict.get('reasoning', '')}")
                    
                    if verdict.get('error') not in ['không có', 'none']:
                        st.markdown(f"**Error:** {verdict.get('error')}")
                    if verdict.get('correction') not in ['không có', 'none']:
                        st.markdown(f"**Correction:** {verdict.get('correction')}")
            
        except Exception as e:
            st.error(f"❌ Pipeline thất bại: {e}")
            import traceback
            with st.expander("Chi tiết lỗi"):
                st.code(traceback.format_exc())
