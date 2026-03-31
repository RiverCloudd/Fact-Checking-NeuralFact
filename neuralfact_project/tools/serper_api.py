from urllib.parse import urlparse
import requests
import os
from core.config import SERPER_API_KEY
import csv
import re
from bs4 import BeautifulSoup
from functools import lru_cache

# Load source domains from media bias CSV at module level (once)
_ALL_SOURCE_DOMAINS = set()
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "media-bias-scrubbed-results.csv")
if os.path.exists(_CSV_PATH):
    with open(_CSV_PATH, "r", encoding="utf-8") as _f:
        reader = csv.DictReader(_f)
        for _row in reader:
            raw_url = _row.get("url", "").strip()
            if not raw_url:
                continue
            # Handle both formats: "https://example.com" and "example.com"
            if raw_url.startswith("http"):
                domain = urlparse(raw_url).netloc.lower()
            else:
                domain = raw_url.lower()
            
            # Normalize: remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            
            if domain:
                _ALL_SOURCE_DOMAINS.add(domain)

print(f"✅ Loaded {_CSV_PATH}: {len(_ALL_SOURCE_DOMAINS)} verified sources")



def _get_domain(link: str) -> str:
    domain = urlparse(link).netloc.lower()
    # Normalize: remove www. prefix if exists (to match CSV format)
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

@lru_cache(maxsize=128)
def _fetch_longer_snippet(url: str, max_length: int = 400) -> str:
    """Fetch page and extract longer snippet from first paragraph(s)
    
    Args:
        url: Article URL
        max_length: Max characters to return
        
    Returns:
        Longer snippet or empty string if failed
    """
    try:
        response = requests.get(url, timeout=2)
        response.encoding = 'utf-8'
        html = response.text

        soup = BeautifulSoup(html, "lxml")
        
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "noscript"]):
            script.decompose()

        paragraphs = soup.find_all('p')
        
        if not paragraphs:
            # Fallback for divs with content-related classes/ids if no <p> tags
            content_div = soup.find('div', class_=re.compile(r'content|article|body', re.I))
            if content_div:
                paragraphs = content_div.find_all(['p', 'div'])

        if paragraphs:
            # Join text from first 3-5 significant paragraphs
            valid_texts = []
            current_length = 0
            for p in paragraphs:
                text = p.get_text(separator=' ', strip=True)
                # Hạ mức filter từ 40 xuống 20 để không bỏ sót các bullet points ngắn như "Tên đầy đủ:..."
                if len(text) > 20: 
                    valid_texts.append(text)
                    current_length += len(text)
                
                # Tính tổng độ dài, nếu đã đủ max_length thì dừng sớm
                if current_length > max_length:
                    break

            if valid_texts:
                snippet = ' '.join(valid_texts)
                snippet = re.sub(r'\s+', ' ', snippet).strip()
                return snippet[:max_length]
    except Exception as e:
        pass

    return ""

def _is_known_source(link: str) -> bool:
    domain = _get_domain(link)
    # 1. Auto-pass cho các trang web nhà nước và giáo dục VN
    if domain.endswith(".gov.vn") or domain.endswith(".edu.vn"):
        return True
        
    # 2. TÍNH NĂNG MỚI: Auto-pass cho các trang tài liệu công nghệ
    if domain.endswith(".dev") or domain.endswith(".io") or domain.startswith("docs."):
        return True
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
            answer_snippet = answer_box.get("answer") or answer_box.get("snippet", "")
            
            # Determine verification tier
            if answer_link:
                if _is_known_source(answer_link):
                    trust_tier = "verified"
                else:
                    trust_tier = "unverified"
            else:
                trust_tier = "unverified"
            
            if answer_snippet:
                # Try to fetch longer snippet if too short
                if len(answer_snippet) < 150 and answer_link:
                    longer = _fetch_longer_snippet(answer_link)
                    if longer:
                        answer_snippet = longer
                
                evidences.append(_make_evidence_item(
                    title="Google Answer",
                    snippet=answer_snippet,
                    url=answer_link,
                    source_type="answer_box",
                    tier=trust_tier,
                ))
        
        # 2. Get knowledge graph if available
        if "knowledgeGraph" in search_data:
            kg = search_data["knowledgeGraph"]
            description = kg.get("description", "")
            kg_url = kg.get("website", "") or kg.get("descriptionLink", "")
            
            # Determine verification tier
            if kg_url:
                if _is_known_source(kg_url):
                    trust_tier = "verified"
                else:
                    trust_tier = "unverified"
            else:
                trust_tier = "unverified"
            
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
                snippet = result.get("snippet", "").strip()
                link = result.get("link", "")
                
                if snippet and link and _is_known_source(link):
                    # If snippet too short, try to fetch longer one
                    if len(snippet) < 150:
                        longer = _fetch_longer_snippet(link)
                        if longer:
                            snippet = longer
                    
                    evidences.append(_make_evidence_item(
                        title=result.get("title", ""),
                        snippet=snippet,
                        url=link,
                        source_type="organic",
                        tier="verified"
                    ))
                    
            # Lần 2 (FALLBACK): Nếu bộ lọc whitelist ở trên chém sạch kết quả (evidences rỗng)
            # Ta sẽ vơ vét các nguồn bình thường
            if not evidences:
                for result in raw_organics[:top_k]:
                    snippet = result.get("snippet", "").strip()
                    link = result.get("link", "")
                    
                    if snippet and link:
                        # If snippet too short, try to fetch longer one
                        if len(snippet) < 150:
                            longer = _fetch_longer_snippet(link)
                            if longer:
                                snippet = longer
                        
                        tier = "unverified"
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