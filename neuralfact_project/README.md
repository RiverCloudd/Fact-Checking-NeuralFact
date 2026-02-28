# 🕵️ NeuralFact - Hệ thống Kiểm chứng Tin giả

Hệ thống kiểm chứng thông tin tự động cho tiếng Việt sử dụng **LangGraph** + **Hybrid RAG** + **Vietnamese Embeddings**.

---

## ✨ Tính năng

- 🔍 **Hybrid Search**: BM25 (keyword) + Semantic search (Vietnamese embeddings)
- 🇻🇳 **Vietnamese Optimized**: Sử dụng vietnamese-sbert model
- 📊 **LangGraph Pipeline**: 5 bước tự động (Decompose → Check-worthy → Query Gen → Retrieve → Verify)
- 🗄️ **Qdrant Vector DB**: Lưu trữ 1.3M+ bài báo tiếng Việt
- 🌐 **Serper API**: Tìm kiếm real-time trên Google
- 💰 **Cost Tracking**: Theo dõi chi phí token

---

## 🚀 Quick Start (10 phút)

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 3. Upload dataset (5,000 bài báo tiếng Việt)

```bash
python upload_to_qdrant.py --limit 5000
```

⏱️ Thời gian: ~15 phút

### 4. Cấu hình API Keys

Tạo file `.env`:

```env
DEEPSEEK_API_KEY=your_key_here
SERPER_API_KEY=your_key_here
```

### 5. Chạy ứng dụng

```bash
streamlit run app.py
```

---

## 📁 Cấu trúc dự án

```
neuralfact_project/
├── app.py                  # Main Streamlit app
├── test_ui.py              # Component testing UI
├── upload_to_qdrant.py     # Upload dataset to Qdrant
├── test_qdrant_search.py   # Test search functionality
├── test_qdrant_connection.py # Test Qdrant connection
├── requirements.txt        # Dependencies
├── .env                    # API Keys (không push lên Git)
├── config/                 # Configuration
│   ├── prompts_vi.yaml     # Vietnamese prompts
│   └── prompts_config.py
├── core/                   # Core system
│   └── config.py
├── pipeline/               # LangGraph pipeline
│   ├── state.py
│   ├── nodes.py            # 5 nodes logic
│   └── graph.py
├── tools/                  # External tools
│   ├── qdrant_db.py        # Qdrant + Vietnamese embeddings
│   └── serper_api.py       # Google Search
└── knowlede-base/          # Vietnamese news dataset (1.3M)
    ├── train-00000-of-00002.parquet
    └── train-00001-of-00002.parquet
```

---

## 🔍 Pipeline (5 bước)

```
Input: "Obama là tổng thống thứ mấy của Mỹ?"

1️⃣ DECOMPOSE
   → Tách thành claims: ["Obama là tổng thống của Mỹ"]

2️⃣ CHECK-WORTHY
   → Lọc claims cần verify: ["Có - Obama là tổng thống của Mỹ"]

3️⃣ QUERY GENERATION  
   → Tạo queries: ["Obama president USA number", "Barack Obama"]

4️⃣ RETRIEVE
   → Qdrant (local): [Vietnamese news about Obama...]
   → Serper (web): [Google results...]

5️⃣ VERIFY
   → Phân tích → "ĐÚNG - Obama là tổng thống thứ 44"
```

---

## 🇻🇳 Vietnamese Embedding Model

**Model:** `keepitreal/vietnamese-sbert`

---

## 📊 Upload Dataset Options

### Quick Test (1,000 bài - 3 phút)
```bash
python upload_to_qdrant.py --limit 1000
```

### Testing (10,000 bài)
```bash
python upload_to_qdrant.py --limit 10000
```

### Production (100,000 bài)
```bash
python upload_to_qdrant.py --limit 100000
```

### Full Dataset (1.3M bài)
```bash
python upload_to_qdrant.py --file knowlede-base/train-00000-of-00002.parquet
python upload_to_qdrant.py --file knowlede-base/train-00001-of-00002.parquet
```

---

## 🧪 Testing

### Test UI (component by component)
```bash
streamlit run test_ui.py
```

### Test full pipeline
```bash
streamlit run app.py
```

---

## 📊 Dataset

**Vietnamese News Dataset (1.3M articles)**
- **Source:** `knowlede-base/train-*.parquet`
- **Categories:** 11 topics (Thời sự, Thế giới, Kinh doanh, Khoa học, etc.)
- **Fields:** label, title, description, text
- **Total:** 1,348,717 articles

## 🛠️ Configuration

### Qdrant Settings
- **Host:** localhost:6333
- **Collection:** factcheck_evidence
- **Vector dimension:** 384
- **Distance:** COSINE

### LangGraph Pipeline
- **Nodes:** 5 (decompose, checkworthy, qgen, retrieve, verify)
- **State:** GraphState with claims, queries, evidences, results
- **Retry:** 3 attempts for each node

---

```bash
# Start trong 3 commands:
docker run -p 6333:6333 qdrant/qdrant
python upload_to_qdrant.py --limit 5000
streamlit run app.py
```
