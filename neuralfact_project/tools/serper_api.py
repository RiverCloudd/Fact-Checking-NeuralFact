from urllib.parse import urlparse
import requests
import os
from core.config import SERPER_API_KEY
import csv

# Load source domains and unreliable sources from media bias CSV at module level (once)
_UNRELIABLE_DOMAINS = set()
_ALL_SOURCE_DOMAINS = set()
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "media-bias-scrubbed-results.csv")
if os.path.exists(_CSV_PATH):
    with open(_CSV_PATH, "r", encoding="utf-8") as _f:
        for _row in csv.DictReader(_f):
            raw_url = _row.get("url", "").strip()
            domain = urlparse(raw_url).netloc.lower().lstrip("www.")
            if domain:
                _ALL_SOURCE_DOMAINS.add(domain)
                rating = _row.get("factual_reporting_rating", "").strip()
                if rating in ("LOW", "VERY LOW"):
                    _UNRELIABLE_DOMAINS.add(domain)

print(f"Loaded {_CSV_PATH}: {_ALL_SOURCE_DOMAINS.__len__()} sources, {_UNRELIABLE_DOMAINS.__len__()} unreliable")



def _get_domain(link: str) -> str:
    return urlparse(link).netloc.lower()

def _is_unreliable(link: str) -> bool:
    domain = _get_domain(link)
    # Trả về True nếu domain là baddomain.com hoặc abc.baddomain.com
    return any(domain == bad or domain.endswith("." + bad) for bad in _UNRELIABLE_DOMAINS)

def _is_known_source(link: str) -> bool:
    domain = _get_domain(link)
    return any(domain == known or domain.endswith("." + known) for known in _ALL_SOURCE_DOMAINS)

def _compose_evidence_text(title: str = "", snippet: str = "", url: str = "") -> str:
    parts = []
    clean_title = str(title or "").strip()
    clean_snippet = str(snippet or "").strip()
    clean_url = str(url or "").strip()

    if clean_title:
        parts.append(f"[{clean_title}]")
    if clean_snippet:
        parts.append(clean_snippet)
    if clean_url:
        parts.append(f"Nguồn: {clean_url}")

    return "\n".join(parts).strip()

def _make_evidence_item(
    *,
    title: str = "",
    snippet: str = "",
    url: str = "",
    source_type: str = "organic",
    source_name: str = "google-serper",
    tier: str = "unrated",
) -> dict:
    return {
        "title": str(title or "").strip(),
        "snippet": str(snippet or "").strip(),
        "url": str(url or "").strip(),
        "text": _compose_evidence_text(title=title, snippet=snippet, url=url),
        "source_type": source_type,
        "source_name": source_name,
        "tier": tier,
    }

def search_google(query: str, top_k: int = 3) -> list:
    """Gọi Serper API lấy kết quả tìm kiếm (Tối ưu cho Tiếng Việt)
    
    Args:
        query: Từ khóa tìm kiếm
        top_k: Số kết quả trả về
        
    Returns:
        list: Danh sách evidence objects có metadata
    """
    headers = {
        "X-API-KEY": SERPER_API_KEY, 
        "Content-Type": "application/json"
    }
    
    payload = {
        "q": query, 
        "num": top_k * 3,  # Lấy nhiều hơn top_k để có thể lọc sau
        "gl": "vn",
        "hl": "vi",
        "autocorrect": True # Tự động sửa lỗi chính tả trong query
    }
    
    evidences = []
    timeout_seconds = float(os.getenv("SERPER_TIMEOUT_SECONDS", "6"))
    
    try:
        # Thêm timeout để tránh treo pipeline
        resp = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
            timeout=timeout_seconds 
        )
        
        resp.raise_for_status()
        search_data = resp.json()
        
        # 1. Check for answer box first (most reliable)
        if "answerBox" in search_data:
            answer_box = search_data["answerBox"]
            answer_link = answer_box.get("link", "")
            
            # Determine trust tier
            if answer_link:
                if _is_unreliable(answer_link):
                    trust_tier = "unreliable"
                elif _is_known_source(answer_link):
                    trust_tier = "high_trust"
                else:
                    trust_tier = "unrated"
            else:
                trust_tier = "unrated"
            
            if "answer" in answer_box:
                evidences.append(_make_evidence_item(
                    title="Google Answer",
                    snippet=answer_box["answer"],
                    url=answer_link,
                    source_type="answer_box",
                    tier=trust_tier,
                ))
            elif "snippet" in answer_box:
                evidences.append(_make_evidence_item(
                    title="Google Snippet",
                    snippet=answer_box["snippet"],
                    url=answer_link,
                    source_type="answer_box",
                    tier=trust_tier,
                ))
        
        # 2. Get knowledge graph if available
        if "knowledgeGraph" in search_data:
            kg = search_data["knowledgeGraph"]
            description = kg.get("description", "")
            kg_url = kg.get("website", "") or kg.get("descriptionLink", "")
            
            # Determine trust tier
            if kg_url:
                if _is_unreliable(kg_url):
                    trust_tier = "unreliable"
                elif _is_known_source(kg_url):
                    trust_tier = "high_trust"
                else:
                    trust_tier = "unrated"
            else:
                trust_tier = "unrated"
            
            if description:
                evidences.append(_make_evidence_item(
                    title=kg.get("title", "Knowledge Graph"),
                    snippet=description,
                    url=kg_url,
                    source_type="knowledge_graph",
                    tier=trust_tier,
                ))  
        
        # 3. Get organic results
        if "organic" in search_data:
            raw_organics = search_data["organic"]
            
            # Lần 1: Cố gắng lấy các nguồn uy tín (có trong CSV)
            for result in raw_organics:
                snippet = result.get("snippet", "")
                link = result.get("link", "")
                
                if snippet and link and not _is_unreliable(link) and _is_known_source(link):
                    evidences.append(_make_evidence_item(
                        title=result.get("title", ""),
                        snippet=snippet,
                        url=link,
                        source_type="organic",
                        tier="high_trust" # ✅ Uy tín cao
                    ))
                    
            # Lần 2 (FALLBACK): Nếu bộ lọc whitelist ở trên chém sạch kết quả (evidences rỗng)
            # Ta sẽ vơ vét các nguồn bình thường, miễn là nó KHÔNG nằm trong danh sách đen Unreliable
            if not evidences:
                for result in raw_organics[:top_k]:
                    snippet = result.get("snippet", "")
                    link = result.get("link", "")
                    
                    if snippet and link:
                        if _is_unreliable(link):
                            tier = "unreliable"  # ❌ Không uy tín
                        else:
                            tier = "unrated"  # ⚠️ Chưa rõ uy tín
                        
                        evidences.append(_make_evidence_item(
                            title=result.get("title", ""),
                            snippet=snippet,
                            url=link,
                            source_type="organic",
                            tier=tier
                        ))
                    
    except requests.exceptions.Timeout:
        print(f"Serper API timeout khi tìm kiếm: '{query}'")
    except requests.exceptions.RequestException as e:
        print(f"Lỗi kết nối HTTP với Serper: {e}")
    except Exception as e:
        print(f"Lỗi không xác định khi parse dữ liệu Serper: {e}")
    
    # Deduplicate, preserve order, and hard cap to top_k results.
    unique_evidences = []
    seen = set()
    for ev in evidences:
        key = (ev.get("url") or ev.get("text") or "").strip()
        if key and key not in seen:
            unique_evidences.append(ev)
            seen.add(key)
        if len(unique_evidences) >= top_k:
            break

    return unique_evidences