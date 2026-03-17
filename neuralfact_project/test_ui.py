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

st.set_page_config(page_title="NeuralFact - Component Testing", layout="wide")

st.title("🧪 NeuralFact Component Testing")
st.markdown("Test từng bước của pipeline với giao diện trực quan")

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
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    serper_key = os.getenv("SERPER_API_KEY")
    
    if deepseek_key:
        st.success(f"✅ DeepSeek: {deepseek_key[:10]}...")
    else:
        st.error("❌ DeepSeek API key missing")
    
    if serper_key:
        st.success(f"✅ Serper: {serper_key[:10]}...")
    else:
        st.warning("⚠️ Serper API key missing")
    
    st.divider()
    
    # Current tokens
    st.metric("Input Tokens", st.session_state.state['prompt_tokens'])
    st.metric("Output Tokens", st.session_state.state['completion_tokens'])
    
    total_tokens = st.session_state.state['prompt_tokens'] + st.session_state.state['completion_tokens']
    if total_tokens > 0:
        input_cost = (st.session_state.state['prompt_tokens'] / 1_000_000) * PRICE_1M_INPUT_TOKENS
        output_cost = (st.session_state.state['completion_tokens'] / 1_000_000) * PRICE_1M_OUTPUT_TOKENS
        total_cost = input_cost + output_cost
        st.metric("Total Cost", f"${total_cost:.6f}")
    
    if st.button("🔄 Reset State"):
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
