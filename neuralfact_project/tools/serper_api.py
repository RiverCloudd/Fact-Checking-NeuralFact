import csv
import os
from urllib.parse import urlparse

import requests
import os
import os
from core.config import SERPER_API_KEY

# Load unreliable sources from media bias CSV at module level (once)
_UNRELIABLE_DOMAINS = set()
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "media-bias-scrubbed-results.csv")
if os.path.exists(_CSV_PATH):
    with open(_CSV_PATH, "r", encoding="utf-8") as _f:
        for _row in csv.DictReader(_f):
            rating = _row.get("factual_reporting_rating", "").strip()
            if rating in ("LOW", "VERY LOW"):
                raw_url = _row.get("url", "").strip()
                domain = urlparse(raw_url).netloc.lower().lstrip("www.")
                if domain:
                    _UNRELIABLE_DOMAINS.add(domain)


def _is_unreliable(link: str) -> bool:
    """Check if a URL's domain is in the unreliable sources list."""
    domain = urlparse(link).netloc.lower().lstrip("www.")
    return domain in _UNRELIABLE_DOMAINS


# Load unreliable sources from media bias CSV at module level (once)
_UNRELIABLE_DOMAINS = set()
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "media-bias-scrubbed-results.csv")
if os.path.exists(_CSV_PATH):
    with open(_CSV_PATH, "r", encoding="utf-8") as _f:
        for _row in csv.DictReader(_f):
            rating = _row.get("factual_reporting_rating", "").strip()
            if rating in ("LOW", "VERY LOW"):
                raw_url = _row.get("url", "").strip()
                domain = urlparse(raw_url).netloc.lower().lstrip("www.")
                if domain:
                    _UNRELIABLE_DOMAINS.add(domain)

def _is_unreliable(link: str) -> bool:
    """Check if a URL's domain is in the unreliable sources list."""
    domain = urlparse(link).netloc.lower().lstrip("www.")
    return domain in _UNRELIABLE_DOMAINS

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
        "num": top_k,
        "num": top_k,
        "gl": "vn",
        "hl": "vi",
        "autocorrect": True # Tự động sửa lỗi chính tả trong query
    }
    
    evidences = []
    timeout_seconds = float(os.getenv("SERPER_TIMEOUT_SECONDS", "6"))
    timeout_seconds = float(os.getenv("SERPER_TIMEOUT_SECONDS", "6"))
    
    try:
        # Thêm timeout để tránh treo pipeline
        resp = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
            timeout=timeout_seconds 
            timeout=timeout_seconds 
        )
        
        resp.raise_for_status()
        search_data = resp.json()
        
        # 1. Check for answer box first (most reliable)
        if "answerBox" in search_data:
            answer_box = search_data["answerBox"]
            if "answer" in answer_box:
                evidences.append(_make_evidence_item(
                    title="Google Answer",
                    snippet=answer_box["answer"],
                    url=answer_box.get("link", ""),
                    source_type="answer_box",
                ))
            elif "snippet" in answer_box:
                evidences.append(_make_evidence_item(
                    title="Google Snippet",
                    snippet=answer_box["snippet"],
                    url=answer_box.get("link", ""),
                    source_type="answer_box",
                ))
                
        # 2. Get knowledge graph if available
        if "knowledgeGraph" in search_data:
            kg = search_data["knowledgeGraph"]
            description = kg.get("description", "")
            if description:
                evidences.append(_make_evidence_item(
                    title=kg.get("title", "Knowledge Graph"),
                    snippet=description,
                    url=kg.get("website", "") or kg.get("descriptionLink", ""),
                    source_type="knowledge_graph",
                ))
        
        # 3. Get organic results (filter out unreliable sources)
        if "organic" in search_data:
            for result in search_data["organic"]:
                if len(evidences) >= top_k:
                    break
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                link = result.get("link", "")
                
                if snippet and not _is_unreliable(link):
                    evidence = f"[{title}]\n{snippet}\nNguồn: {link}"
                    evidences.append(evidence)
                    
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
        key = ev.strip()
        if key and key not in seen:
            unique_evidences.append(ev)
            seen.add(key)
        if len(unique_evidences) >= top_k:
            break

    return unique_evidences