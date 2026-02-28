"""Logic kết nối Qdrant Vector DB (Hybrid Search: BM25 + Semantic)

Qdrant là vector database để lưu trữ và tìm kiếm bằng chứng đã thu thập trước đó.
Sử dụng hybrid search kết hợp:
- BM25 (keyword matching) thông qua fastembed
- Semantic search (Vietnamese embeddings) thông qua sentence-transformers
"""
import os
from typing import List, Optional

# Check dependencies
try:
    from qdrant_client import QdrantClient, models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("⚠️ Warning: qdrant-client không được cài đặt. Chạy: pip install qdrant-client")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ Warning: sentence-transformers không được cài đặt. Chạy: pip install sentence-transformers")

try:
    from fastembed import SparseTextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False
    print("⚠️ Warning: fastembed không được cài đặt. Chạy: pip install fastembed")

# Cập nhật model đồng bộ với file upload
VIETNAMESE_MODEL = "bkai-foundation-models/vietnamese-bi-encoder" 
SPARSE_MODEL = "Qdrant/bm25"


class QdrantDB:
    """Qdrant Vector Database Client with Hybrid Search
    
    Uses bkai-foundation-models/vietnamese-bi-encoder cho Semantic
    Uses Qdrant/bm25 (fastembed) cho Keyword matching
    """
    
    def __init__(self, collection_name: str = "factcheck_evidence", 
                 host: str = "localhost", port: int = 6333):
        """Khởi tạo Qdrant client"""
        self.client = None
        self.model = None
        self.sparse_model = None
        self.collection_name = collection_name
        self.use_hybrid = True
        
        if not (QDRANT_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE and FASTEMBED_AVAILABLE):
            return
            
        try:
            # Connect to Qdrant
            self.client = QdrantClient(host=host, port=port)
            
            # Load Dense Model (Semantic)
            print(f"Loading Dense model: {VIETNAMESE_MODEL}")
            self.model = SentenceTransformer(VIETNAMESE_MODEL)
            print(f"Dense Model loaded (dimension: {self.model.get_sentence_embedding_dimension()})")
            
            # Load Sparse Model (BM25)
            print(f"Loading Sparse model: {SPARSE_MODEL}")
            self.sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)
            print(f"Sparse Model loaded")
            
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if collection_name not in collection_names:
                print(f"Collection '{collection_name}' không tồn tại")
                print(f"Hãy chạy script upload data trước.")
                
        except Exception as e:
            print(f"Không thể kết nối Qdrant: {e}")
            self.client = None
    
    def search(self, query: str, top_k: int = 3) -> List[str]:
        """Tìm kiếm bằng chứng với hybrid search (BM25 + Semantic)
        
        Args:
            query: Câu truy vấn
            top_k: Số kết quả trả về
            
        Returns:
            list: Danh sách các snippet bằng chứng (với metadata)
        """
        if self.client is None or self.model is None or self.sparse_model is None:
            return []
        
        try:
            # 1. Generate Dense Vector (Semantic)
            query_dense = self.model.encode(query).tolist()
            
            if self.use_hybrid:
                # 2. Generate Sparse Vector (BM25)
                query_sparse = next(self.sparse_model.embed([query]))
                sparse_vector = models.SparseVector(
                    indices=query_sparse.indices.tolist(),
                    values=query_sparse.values.tolist()
                )
                
                # 3. Hybrid Search: Kết hợp qua Prefetch và RRF
                results = self.client.query_points(
                    collection_name=self.collection_name,
                    prefetch=[
                        models.Prefetch(
                            query=sparse_vector,
                            using="sparse",
                            limit=top_k * 2,
                        ),
                        models.Prefetch(
                            query=query_dense,
                            using="dense",
                            limit=top_k * 2,
                        )
                    ],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=top_k
                )
            else:
                # Fallback: Chỉ tìm kiếm bằng Semantic (Dense) thuần túy
                print("Warning: Hybrid search tạm thời bị vô hiệu hóa. Chỉ sử dụng Semantic search.")
                results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_dense,
                    using="dense",
                    limit=top_k
                )
            
            # Format results
            evidences = []
            for hit in results.points:
                # Lấy dữ liệu payload dựa theo cấu trúc ta đã upload
                text = hit.payload.get('text', '')
                source = hit.payload.get('source', 'Unknown')
                category = hit.payload.get('category', '')
                score = hit.score
                
                # Format: [Category | Source] Text (score: 0.XX)
                if category:
                    evidence = f"[{category} | {source}] {text} (score: {score:.3f})"
                else:
                    evidence = f"[{source}] {text} (score: {score:.3f})"
                evidences.append(evidence)
            
            return evidences
            
        except Exception as e:
            print(f"Lỗi khi tìm kiếm Qdrant: {e}")
            import traceback
            traceback.print_exc()
            return []


# Global Qdrant instance
_qdrant_instance = None

def get_qdrant():
    """Lấy Qdrant instance (singleton)"""
    global _qdrant_instance
    if _qdrant_instance is None:
        _qdrant_instance = QdrantDB()
    return _qdrant_instance


def search_qdrant(query: str, top_k: int = 3) -> List[str]:
    """Tìm kiếm bằng chứng từ Qdrant Vector DB
    
    Args:
        query: Câu truy vấn
        top_k: Số kết quả trả về
        
    Returns:
        list: Danh sách các snippet bằng chứng
    """
    qdrant = get_qdrant()
    return qdrant.search(query, top_k)