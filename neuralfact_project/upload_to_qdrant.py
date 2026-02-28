"""
Upload Vietnamese News Classification Dataset (1.3M) to Qdrant - BẢN TỐI ƯU TỐC ĐỘ
- Tự động nhận diện và vắt kiệt GPU (CUDA)
- Tạm tắt Indexing HNSW để nhồi data siêu tốc
- Giao thức gRPC và Upload song song
"""
import json
import argparse
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import gc
import torch

print("="*60)
print("🚀 UPLOAD 1.3M VIETNAMESE NEWS TO QDRANT (BẢN TỐI ƯU TỐC ĐỘ)")
print("="*60)

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--file', default='knowledge-base/train-00001-of-00002.parquet', help='Đường dẫn file dataset')
parser.add_argument('--collection', default='factcheck_evidence', help='Tên Collection trên Qdrant')
# Tăng batch-size mặc định lên 512 để tận dụng GPU tốt hơn
parser.add_argument('--batch-size', type=int, default=512, help='Kích thước batch để encode') 
parser.add_argument('--limit', type=int, default=None, help='Giới hạn số record để test')
args = parser.parse_args()

VIETNAMESE_MODEL = "bkai-foundation-models/vietnamese-bi-encoder" 
SPARSE_MODEL = "Qdrant/bm25"

CATEGORY_MAP = {
    0: 'Thời sự', 1: 'Thế giới', 2: 'Kinh doanh', 3: 'Khoa học',
    4: 'Bất động sản', 5: 'Sức khỏe', 6: 'Thể thao', 7: 'Giải trí',
    8: 'Pháp luật', 9: 'Giáo dục', 10: 'Đời sống'
}

print("\n1. Đang kiểm tra thư viện...")
try:
    from qdrant_client import QdrantClient, models
    from sentence_transformers import SentenceTransformer
    from fastembed import SparseTextEmbedding
    print("✅ Các thư viện cốt lõi OK")
except ImportError as e:
    print(f"❌ Thiếu thư viện: {e}")
    exit(1)

# Kiểm tra thiết bị tính toán (GPU vs CPU)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"⚡ Đã phát hiện phần cứng tính toán: {DEVICE.upper()}")

print("\n2. Kết nối tới Qdrant (gRPC Mode)...")
try:
    # Chuyển sang dùng gRPC port 6334 để tăng tốc I/O
    client = QdrantClient(host="localhost", grpc_port=6334, prefer_grpc=True, timeout=120)
    print("✅ Kết nối Qdrant gRPC thành công")
except Exception as e:
    print(f"❌ Không thể kết nối Qdrant: {e}")
    exit(1)

print("\n3. Đang tải AI Models...")
try:
    print(f"   Dense Model: {VIETNAMESE_MODEL}")
    # Đẩy model lên GPU
    dense_model = SentenceTransformer(VIETNAMESE_MODEL, device=DEVICE)
    embedding_dim = dense_model.get_sentence_embedding_dimension()
    
    print(f"   Sparse Model (BM25): {SPARSE_MODEL}")
    sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)
    print("✅ Tải models thành công!")
except Exception as e:
    print(f"❌ Lỗi khi tải model: {e}")
    exit(1)

print(f"\n4. Thiết lập Collection '{args.collection}'...")
try:
    collections = [c.name for c in client.get_collections().collections]
    
    if args.collection not in collections:
        # TRƯỜNG HỢP 1: CHƯA CÓ COLLECTION -> TẠO MỚI
        print(f"   Collection chưa tồn tại. Đang tạo mới...")
        client.create_collection(
            collection_name=args.collection,
            vectors_config={
                "dense": models.VectorParams(size=embedding_dim, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(index=models.SparseIndexParams(on_disk=True))
            },
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=0) 
        )
        global_id = 0
        print(f"✅ Đã tạo Hybrid Collection mới. Bắt đầu ID từ: {global_id}")
        
    else:
        # TRƯỜNG HỢP 2: ĐÃ CÓ COLLECTION -> NỐI DỮ LIỆU
        collection_info = client.get_collection(args.collection)
        global_id = collection_info.points_count
        
        print(f"   Collection đã tồn tại với {global_id:,} bản ghi.")
        print(f"   Sẽ NỐI TIẾP dữ liệu. Bắt đầu ID từ: {global_id}")
        
        # Vẫn phải tắt Indexing tạm thời để nhồi tiếp file 2 cho nhanh
        client.update_collection(
            collection_name=args.collection,
            optimizer_config=models.OptimizersConfigDiff(indexing_threshold=0)
        )
        print("✅ Đã tắt tạm thời Indexing để upload file mới.")

except Exception as e:
    print(f"❌ Lỗi thiết lập Collection: {e}")
    exit(1)

print(f"\n5. Đọc dữ liệu từ {args.file}...")
try:
    file_ext = Path(args.file).suffix.lower()
    if file_ext == '.parquet':
        df = pd.read_parquet(args.file)
    elif file_ext == '.csv':
        df = pd.read_csv(args.file)
    elif file_ext == '.json':
        df = pd.read_json(args.file)
    else:
        raise ValueError("Định dạng file không được hỗ trợ.")

    if args.limit:
        df = df.head(args.limit)
        
    print(f"✅ Đã tải {len(df):,} bản ghi.")
except Exception as e:
    print(f"❌ Lỗi đọc dữ liệu: {e}")
    exit(1)

print("\n6. Bắt đầu mã hóa và tải lên Qdrant...")
records = df.to_dict('records')
del df
gc.collect()

def chunk_generator(data, batch_size):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]

total_batches = (len(records) + args.batch_size - 1) // args.batch_size

for batch in tqdm(chunk_generator(records, args.batch_size), total=total_batches, desc="Tiến độ Upload"):
    valid_items = []
    texts_to_encode = []
    
    for item in batch:
        text = str(item.get('text', '')).strip()
        if len(text) > 10:
            valid_items.append(item)
            texts_to_encode.append(text)
            
    if not texts_to_encode:
        continue

    # Encode sẽ cực kỳ nhanh nếu DEVICE = "cuda"
    dense_embeddings = dense_model.encode(texts_to_encode).tolist()
    sparse_embeddings = list(sparse_model.embed(texts_to_encode))
    
    points = []
    for item, dense_vec, sparse_vec, original_text in zip(valid_items, dense_embeddings, sparse_embeddings, texts_to_encode):
        sparse_data = models.SparseVector(
            indices=sparse_vec.indices.tolist(),
            values=sparse_vec.values.tolist()
        )
        
        label_id = int(item.get('label', 0))
        category_name = CATEGORY_MAP.get(label_id, 'Khác')
        
        payload = {
            "title": str(item.get('title', '')),
            "description": str(item.get('description', '')),
            "text": original_text,
            "category_id": label_id,
            "category": category_name,
            "source": "Vietnamese News Dataset (1.3M)"
        }
        
        points.append(models.PointStruct(
            id=global_id,
            vector={"dense": dense_vec, "sparse": sparse_data},
            payload=payload
        ))
        global_id += 1
        
    # Ghi qua gRPC bất đồng bộ (wait=False) để script không bị khựng lại chờ DB
    client.upload_points(
        collection_name=args.collection,
        points=points,
        wait=False 
    )

print("="*60)
print(f"✅ NHỒI DỮ LIỆU HOÀN TẤT! Đã đưa {global_id:,} vectors vào Qdrant.")
print("="*60)

# BƯỚC QUAN TRỌNG: Bật lại Indexing sau khi đã upload xong
print("\n⚙️ Đang bật lại Indexing. Qdrant sẽ tốn một lúc để sắp xếp toàn bộ 1.3M vectors...")
try:
    client.update_collection(
        collection_name=args.collection,
        optimizer_config=models.OptimizersConfigDiff(
            indexing_threshold=20000 # Trả về ngưỡng mặc định để bắt đầu index
        )
    )
    print("✅ Lệnh Indexing đã được gửi thành công. Bạn có thể theo dõi CPU của Docker.")
except Exception as e:
    print(f"❌ Lỗi khi bật lại Indexing: {e}")

# 7. Test Thử Tính Năng Tìm Kiếm (Tạm thời bỏ qua nếu index chưa xong, nhưng data thì đã có)
print("\n7. Test Hybrid Search nhanh...")
try:
    test_query = "thủ tướng chính phủ họp bàn về kinh tế"
    query_dense = dense_model.encode(test_query).tolist()
    query_sparse = next(sparse_model.embed([test_query]))
    
    results = client.query_points(
        collection_name=args.collection,
        prefetch=[
            models.Prefetch(query=models.SparseVector(indices=query_sparse.indices.tolist(), values=query_sparse.values.tolist()), using="sparse", limit=5),
            models.Prefetch(query=query_dense, using="dense", limit=5)
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=2
    )
    
    for i, hit in enumerate(results.points, 1):
        print(f"\n[{i}] Chuyên mục: {hit.payload.get('category')} | Điểm: {hit.score:.4f}")
        print(f"    Tiêu đề: {hit.payload.get('title')}")
        
except Exception as e:
    print(f"❌ Lỗi khi test search: {e} (Có thể do Indexing đang chạy ngầm)")