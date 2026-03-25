# NeuralFact - He thong kiem chung tin gia

NeuralFact la ung dung fact-check tieng Viet su dung:
- LangGraph pipeline
- Hybrid retrieval (Qdrant + Serper)
- DeepSeek API (qua langchain-openai)
- Streamlit UI

## Cong nghe chinh

- Python 3.10+
- Streamlit
- LangGraph
- LangChain OpenAI wrapper
- Qdrant Vector DB
- Sentence Transformers + FastEmbed (hybrid search)
- Serper API

## Yeu cau truoc khi chay

- Python 3.10+
- Docker Desktop (de chay Qdrant)
- API keys:
  - `DEEPSEEK_API_KEY`
  - `SERPER_API_KEY`

## Cai dat (khuyen nghi tren Windows + Conda)

```bash
conda create -n neuralfact python=3.10 -y
conda activate neuralfact
cd neuralfact_project
pip install -r requirements.txt
```

## Cau hinh moi truong

Tao file `.env` trong thu muc `neuralfact_project`:

```env
DEEPSEEK_API_KEY=your_deepseek_key
SERPER_API_KEY=your_serper_key
```

Tu chinh hieu nang (tuy chon):

```env
MAX_CLAIMS=3
SERPER_TOP_K=3
MAX_EVIDENCES_PER_CLAIM=3
LLM_TIMEOUT_SECONDS=12
```

## Chay Qdrant

Cach 1 (khuyen nghi):

```bash
docker compose up -d
```

Cach 2 (mot lenh):

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

## (Tuy chon) Nap du lieu vao Qdrant

Nap nhanh de test:

```bash
python upload_to_qdrant.py --limit 5000
```

Nap nhieu hon:

```bash
python upload_to_qdrant.py --limit 100000
```

## Chay ung dung

```bash
streamlit run app.py
```

## Test UI

```bash
streamlit run test_ui.py
```

## Cau truc thu muc

```text
neuralfact_project/
  app.py
  test_ui.py
  upload_to_qdrant.py
  requirements.txt
  docker-compose.yml
  .env
  core/
  pipeline/
  tools/
  config/
  knowledge-base/
```

## Luu y quan trong

- Project da bo phu thuoc NLTK.
- Fallback tach cau da duoc xu ly bang regex noi bo.
- Neu bi loi thieu package, hay chac chan ban dang o dung env (`conda activate neuralfact`) truoc khi chay.
