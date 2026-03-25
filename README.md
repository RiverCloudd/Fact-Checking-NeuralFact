# Fact-Checking-NeuralFact

Monorepo gom 2 phần chính:

1. `neuralfact_project`: He thong fact-check tieng Viet (Streamlit + LangGraph + Hybrid RAG).
2. `TL-system-4-test-data`: Bo script dich/merge du lieu JSONL phuc vu test.

## 1) NeuralFact App

Tai lieu chi tiet: `neuralfact_project/README.md`

Quick start nhanh:

```bash
cd neuralfact_project
pip install -r requirements.txt
docker compose up -d
streamlit run app.py
```

Neu can upload du lieu len Qdrant:

```bash
python upload_to_qdrant.py --limit 5000
```

## 2) TL System 4 Test Data

Tai lieu chi tiet: `TL-system-4-test-data/README.md`

Quick start nhanh:

```bash
cd TL-system-4-test-data
pip install -r requirements.txt
python translate_jsonl.py --start 1 --end 10
python merge_jsonl.py --folder tl-res
```