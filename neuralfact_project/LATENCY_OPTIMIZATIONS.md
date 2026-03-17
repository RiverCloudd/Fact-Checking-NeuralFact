# Latency Optimizations Summary

- Rút gọn pipeline còn 4 bước: decompose -> checkworthy -> retrieve -> verify.
- Bỏ bước query generation trong luồng chính để giảm số lần gọi LLM.
- Giới hạn số claim xử lý bằng MAX_CLAIMS để giảm tải toàn pipeline.
- Dùng retry có điều kiện cho retrieve (chỉ retry khi toàn bộ claim không có evidence).
- Retrieve chạy song song theo claim bằng ThreadPoolExecutor.
- Dùng Serper snippet/answer box/knowledge graph thay vì fetch full page để giảm I/O.
- Giới hạn số evidence bằng SERPER_TOP_K, MAX_EVIDENCES_PER_CLAIM, VERIFY_EVIDENCES_PER_CLAIM.
- Verify dùng nhiều nguồn trong một lần gọi cho mỗi claim để cân bằng tốc độ và độ chắc chắn.
