import streamlit as st
import time
from pipeline.graph import factcheck_app
from core.config import PRICE_1M_INPUT_TOKENS, PRICE_1M_OUTPUT_TOKENS

st.set_page_config(page_title="NeuralFact Checker", layout="wide")

st.title("🕵️ Hệ thống Kiểm chứng Tin giả (NeuralFact)")
st.markdown("Kiến trúc **Hybrid RAG** với **Loki Pipeline** và **LangGraph**")

user_input = st.text_area("Nhập mệnh đề cần kiểm chứng:")

if st.button("Kiểm tra ngay", type="primary"):
    if not user_input.strip():
        st.warning("Vui lòng nhập văn bản!")
    else:
        with st.spinner("Đang chạy Pipeline (Decompose ➡ Retrieve ➡ Verify)..."):
            start_time = time.time()
            
            initial_state = {
                "input_text": user_input, "claims": [], "checkworthy_claims": [],
                "queries": {}, "evidence": {}, "verdicts": {}, "retry_count": 0,
                "prompt_tokens": 0, "completion_tokens": 0
            }
            
            try:
                # Gọi hệ thống LangGraph từ file pipeline/graph.py
                final_state = factcheck_app.invoke(initial_state)
                
                latency = round(time.time() - start_time, 2)
                prompt_tokens = final_state.get("prompt_tokens", 0)
                completion_tokens = final_state.get("completion_tokens", 0)
                total_tokens = prompt_tokens + completion_tokens
                
                # Calculate cost based on input and output token prices
                input_cost = (prompt_tokens / 1_000_000) * PRICE_1M_INPUT_TOKENS
                output_cost = (completion_tokens / 1_000_000) * PRICE_1M_OUTPUT_TOKENS
                total_cost = round(input_cost + output_cost, 6)
                
                st.success("Hoàn tất kiểm chứng!")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Thời gian (Latency)", f"{latency}s")
                col2.metric("Input Tokens", f"{prompt_tokens}")
                col3.metric("Output Tokens", f"{completion_tokens}")
                col4.metric("Chi phí ước tính", f"${total_cost}")
                
                st.divider()
                st.subheader("📊 Kết quả chi tiết")
                
                for claim, verdict_data in final_state["verdicts"].items():
                    with st.expander(f"Mệnh đề: {claim}", expanded=True):
                        factuality = verdict_data.get("factuality", "NEI")
                        reasoning = verdict_data.get("reasoning", "")
                        error = verdict_data.get("error", "không có")
                        correction = verdict_data.get("correction", "không có")
                        
                        # Display verdict with appropriate color
                        if factuality == True or str(factuality).lower() == "true":
                            st.success(f"**Kết luận:** ✅ ĐÚNG (Supported)")
                        elif factuality == False or str(factuality).lower() == "false":
                            st.error(f"**Kết luận:** ❌ SAI (Refuted)")
                        else:
                            st.warning(f"**Kết luận:** ⚠️ KHÔNG ĐỦ THÔNG TIN (NEI)")
                        
                        st.markdown(f"**Lý do (Reasoning):** {reasoning}")
                        
                        # Show error and correction if exists
                        if error != "không có" and error != "none":
                            st.markdown(f"**Lỗi phát hiện:** {error}")
                        if correction != "không có" and correction != "none":
                            st.markdown(f"**Sửa chữa đề xuất:** {correction}")
                        
                        # Display evidence sources
                        evidences = final_state["evidence"].get(claim, [])
                        if evidences:
                            st.info(f"**Bằng chứng ({len(evidences)} nguồn):**")
                            for i, ev in enumerate(evidences[:3], 1):  # Show top 3
                                with st.container():
                                    st.caption(f"Nguồn {i}:")
                                    st.text(ev[:300] + "..." if len(ev) > 300 else ev)
                        else:
                            st.warning("**Bằng chứng:** Không tìm thấy dữ liệu.")
                        
                        # Show queries used
                        queries = final_state["queries"].get(claim, [])
                        if queries:
                            st.caption(f"*Câu hỏi kiểm tra: {', '.join(queries[:3])}*")

            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {e}")
