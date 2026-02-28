import requests
from core.config import SERPER_API_KEY

def search_google(query: str, top_k: int = 3) -> list:
    """Gọi Serper API lấy kết quả tìm kiếm (Tối ưu cho Tiếng Việt)
    
    Args:
        query: Từ khóa tìm kiếm
        top_k: Số kết quả trả về
        
    Returns:
        list: Danh sách các snippet bằng chứng
    """
    headers = {
        "X-API-KEY": SERPER_API_KEY, 
        "Content-Type": "application/json"
    }
    
    # Thêm gl (quốc gia) và hl (ngôn ngữ) để ép Google trả kết quả tiếng Việt
    payload = {
        "q": query, 
        "num": top_k * 2,
        "gl": "vn",
        "hl": "vi",
        "autocorrect": True # Tự động sửa lỗi chính tả trong query
    }
    
    evidences = []
    
    try:
        # Thêm timeout để tránh treo pipeline
        resp = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
            timeout=10 
        )
        
        # Bắt các lỗi HTTP (401 Unauthorized, 403 Forbidden, 500...)
        resp.raise_for_status()
        search_data = resp.json()
        
        # 1. Check for answer box first (most reliable)
        if "answerBox" in search_data:
            answer_box = search_data["answerBox"]
            if "answer" in answer_box:
                evidences.append(f"[Google Answer] {answer_box['answer']}")
            elif "snippet" in answer_box:
                evidences.append(f"[Google Snippet] {answer_box['snippet']}")
                
        # 2. Get knowledge graph if available
        if "knowledgeGraph" in search_data:
            kg = search_data["knowledgeGraph"]
            description = kg.get("description", "")
            if description:
                evidences.append(f"[Knowledge Graph] {description}")
        
        # 3. Get organic results
        if "organic" in search_data:
            for result in search_data["organic"][:top_k]:
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                link = result.get("link", "")
                
                if snippet:
                    evidence = f"[{title}]\n{snippet}\nNguồn: {link}"
                    evidences.append(evidence)
                    
    except requests.exceptions.Timeout:
        print(f"Serper API timeout khi tìm kiếm: '{query}'")
    except requests.exceptions.RequestException as e:
        print(f"Lỗi kết nối HTTP với Serper: {e}")
    except Exception as e:
        print(f"Lỗi không xác định khi parse dữ liệu Serper: {e}")
    
    return evidences