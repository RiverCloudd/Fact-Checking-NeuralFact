import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import get_llm
from config.prompts_config import prompt_config
from tools.serper_api import search_google
from tools.qdrant_db import search_qdrant
from pipeline.state import FactCheckState
import json
import re

llm = get_llm()


def _stable_dedupe(items):
    """Remove duplicates while preserving original order."""
    unique_items = []
    seen = set()
    for item in items:
        key = str(item).strip()
        if key and key not in seen:
            unique_items.append(item)
            seen.add(key)
    return unique_items


def _normalize_factuality(value):
    """Normalize factuality to boolean. Any non-supported result becomes False."""
    if isinstance(value, bool):
        return value
    value_str = str(value).strip().lower()
    if value_str in {"true", "đúng", "supported", "support", "yes"}:
        return True
    return False


def _compact_evidence(ev: str, max_chars: int) -> str:
    """Trim evidence text to keep multi-source verify prompt short."""
    text = re.sub(r"\s+", " ", ev).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _adaptive_evidence_chars(evidence_count: int) -> int:
    """Auto-size per-evidence length budget for single-pass multi-source verify."""
    # Keep total evidence budget roughly bounded while allowing richer context
    # when fewer sources are provided.
    count = max(1, evidence_count)
    total_budget = 720
    per_ev = total_budget // count
    return max(120, min(320, per_ev))


def _build_verify_context(input_text: str, claim: str) -> str:
    """Build compact context with adaptive length based on text and claim complexity."""
    text = re.sub(r"\s+", " ", (input_text or "")).strip()
    if not text:
        return ""

    # Auto-size context window from content length (no fixed env threshold required).
    # Short texts keep full context; long texts use a bounded adaptive window.
    claim_len = len(re.sub(r"\s+", " ", (claim or "")).strip())
    adaptive_chars = max(260, int(len(text) * 0.42), int(claim_len * 9) + 180)
    adaptive_chars = min(adaptive_chars, 1200)

    if len(text) <= adaptive_chars:
        return text

    claim_text = re.sub(r"\s+", " ", (claim or "")).strip()
    if claim_text:
        lower_text = text.lower()
        lower_claim = claim_text.lower()
        pos = lower_text.find(lower_claim)
        if pos != -1:
            half = adaptive_chars // 2
            start = max(0, pos - half)
            end = min(len(text), start + adaptive_chars)
            # Re-adjust start when reaching end boundary.
            start = max(0, end - adaptive_chars)
            snippet = text[start:end].strip()
            if start > 0:
                snippet = "... " + snippet
            if end < len(text):
                snippet = snippet + " ..."
            return snippet

    # Fallback: keep both opening and ending context instead of only the head.
    side = max(60, (adaptive_chars - 7) // 2)
    return f"{text[:side].rstrip()} ... {text[-side:].lstrip()}"

def clean_json_response(content: str) -> str:
    """Clean LLM response để parse JSON
    
    LLM có thể trả về:
    - Markdown fence: ```json {...} ```
    - Text thừa trước/sau JSON
    - Single quotes thay vì double quotes
    """
    content = content.strip()
    
    # Remove markdown fence
    if content.startswith("```"):
        # Find JSON block
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        content = content.strip()
    
    # Try to extract JSON object from text
    # Find first { and last }
    start_idx = content.find('{')
    end_idx = content.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        content = content[start_idx:end_idx+1]
    
    return content.strip()

def decompose_node(state: FactCheckState):
    """Phase 1: Decompose - Phân tách văn bản thành các mệnh đề nguyên tử"""
    user_input = prompt_config.decompose_prompt.format(
        doc=state["input_text"],
        max_claims=max(1, int(os.getenv("MAX_CLAIMS", "3"))),
    ).strip()
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)

    max_claims = max(1, int(os.getenv("MAX_CLAIMS", "3")))
    use_llm_decompose = os.getenv("USE_LLM_DECOMPOSE", "false").strip().lower() in {"1", "true", "yes"}

    # Ultra-fast mode: sentence split without LLM call.
    if not use_llm_decompose:
        text = state.get("input_text", "")
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 5]
        claims = _stable_dedupe(sentences)[:max_claims]
        if not claims and text.strip():
            claims = [text.strip()[:240]]
        return {
            "claims": claims,
            "retry_count": 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        }
    
    # Keep retries low for latency-first mode.
    decompose_max_retries = max(1, int(os.getenv("DECOMPOSE_MAX_RETRIES", "1")))

    # Try to get valid claims
    claims = []
    for i in range(decompose_max_retries):
        try:
            response = llm.invoke(user_input)
            cleaned_content = clean_json_response(response.content)
            result = json.loads(cleaned_content)
            claims = result.get("claims", [])
            
            # Track tokens
            if hasattr(response, 'response_metadata') and response.response_metadata:
                usage = response.response_metadata.get('token_usage', {})
                prompt_tokens += usage.get('prompt_tokens', 0)
                completion_tokens += usage.get('completion_tokens', 0)
            
            if isinstance(claims, list) and len(claims) > 0:
                break
        except Exception as e:
            print(f"Parse LLM response error (attempt {i+1}): {e}")
            print(f"Raw response: {response.content[:200]}...")
            continue
    
    # Fallback: split by sentences if LLM fails
    if not claims:
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        sentences = nltk.sent_tokenize(state["input_text"])
        claims = [s.strip() for s in sentences if len(s.strip()) >= 3]
    
    claims = claims[:max_claims]

    return {
        "claims": claims, 
        "retry_count": 0,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

def checkworthy_node(state: FactCheckState):
    """Phase 2: Checkworthy - Lọc các mệnh đề đáng kiểm chứng"""
    claims = state["claims"]
    print(f"Checkworthy node: {len(claims)} claims to evaluate")
    print(f"Claims preview: {claims[:3]}...")

    # Fast path: skip LLM filtering to save latency.
    use_llm_checkworthy = os.getenv("USE_LLM_CHECKWORTHY", "false").strip().lower() in {"1", "true", "yes"}
    max_claims = max(1, int(os.getenv("MAX_CLAIMS", "3")))
    if not use_llm_checkworthy:
        quick_claims = [c for c in claims if isinstance(c, str) and len(c.strip()) >= 5][:max_claims]
        return {
            "checkworthy_claims": quick_claims if quick_claims else claims[:max_claims],
            "prompt_tokens": state.get("prompt_tokens", 0),
            "completion_tokens": state.get("completion_tokens", 0)
        }
    
    # Format claims with numbers
    joint_texts = "\n".join([f"{i + 1}. {claim}" for i, claim in enumerate(claims)])
    user_input = prompt_config.checkworthy_prompt.format(texts=joint_texts)
    
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    
    checkworthy_claims = claims  # Default: assume all are checkworthy
    claim2checkworthy = {}
    
    # Keep retries low for latency-first mode.
    checkworthy_max_retries = max(1, int(os.getenv("CHECKWORTHY_MAX_RETRIES", "1")))

    for i in range(checkworthy_max_retries):
        try:
            response = llm.invoke(user_input)
            print(f"Raw checkworthy response: {response.content}")
            cleaned_content = clean_json_response(response.content)
            claim2checkworthy = json.loads(cleaned_content)
            
            # Track tokens
            if hasattr(response, 'response_metadata') and response.response_metadata:
                usage = response.response_metadata.get('token_usage', {})
                prompt_tokens += usage.get('prompt_tokens', 0)
                completion_tokens += usage.get('completion_tokens', 0)
            
            valid_answer = list(
                filter(
                    lambda x: isinstance(x[1], str) and (x[1].strip().lower().startswith("có") or x[1].strip().lower().startswith("không")),
                    claim2checkworthy.items(),
                )
            )
            
            checkworthy_claims_raw = list(
                filter(
                    lambda x: isinstance(x[1], str) and x[1].strip().lower().startswith("có"), 
                    claim2checkworthy.items()
                )
            )
            checkworthy_claims = [x[0] for x in checkworthy_claims_raw]
            
            if len(valid_answer) == len(claim2checkworthy):
                break
        except Exception as e:
            print(f"Checkworthy error (attempt {i+1}): {e}")
            if 'response' in locals():
                print(f"Raw response: {response.content[:300]}...")
            continue
    
    checkworthy_claims = checkworthy_claims[:max_claims]

    return {
        "checkworthy_claims": checkworthy_claims,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

def retrieve_node(state: FactCheckState):
    """Phase 4: Evidence Retrieval - Fast web-first mặc định, Qdrant tùy chọn."""
    claim_queries = state.get("queries", {})
    if not claim_queries:
        base_claims = state.get("checkworthy_claims") or state.get("claims", [])
        claim_queries = {claim: [claim] for claim in base_claims}

    evidence_dict = {}

    # Có thể bật lại Qdrant nếu đã ingest dữ liệu lớn và muốn ưu tiên local retrieval.
    use_qdrant = os.getenv("USE_QDRANT", "false").strip().lower() in {"1", "true", "yes"}
    qdrant_score_threshold = float(os.getenv("QDRANT_SCORE_THRESHOLD", "0.75"))
    serper_top_k = int(os.getenv("SERPER_TOP_K", "3"))
    qdrant_top_k = int(os.getenv("QDRANT_TOP_K", "2"))
    max_evidences_per_claim = int(os.getenv("MAX_EVIDENCES_PER_CLAIM", "3"))
    
    max_parallel_retrieval = max(1, int(os.getenv("MAX_PARALLEL_RETRIEVAL", "3")))

    def _retrieve_single(claim, queries):
        claim_evidences = []
        is_evidence_strong = False
        primary_query = queries[0] if queries else claim
        
        print(f"\n🔍 Đang tìm kiếm bằng chứng cho: '{claim[:50]}...'")

        # BƯỚC 1 (tùy chọn): thử Qdrant nếu được bật.
        if use_qdrant:
            qdrant_results = search_qdrant(primary_query, top_k=qdrant_top_k)
            if qdrant_results:
                claim_evidences.extend(qdrant_results)
                first_result = qdrant_results[0]
                match = re.search(r'\(score:\s*([0-9.]+)\)', first_result)
                if match and float(match.group(1)) >= qdrant_score_threshold:
                    is_evidence_strong = True
                    print("  ✅ Bằng chứng Qdrant đủ mạnh, bỏ qua Google để giảm latency.")

        # BƯỚC 2: fallback web search (mặc định được dùng trong fast mode).
        if not is_evidence_strong:
            serper_results = search_google(primary_query, top_k=serper_top_k)
            if serper_results:
                claim_evidences.extend(serper_results)
                print(f"  🌐 Google trả về {len(serper_results)} bằng chứng.")
            else:
                print("  ❌ Google không có bằng chứng rõ ràng.")

        # BƯỚC 3: dedupe ổn định + giới hạn để verify nhanh hơn.
        unique_evidences = _stable_dedupe(claim_evidences)
        return claim, unique_evidences[:max_evidences_per_claim]

    with ThreadPoolExecutor(max_workers=max_parallel_retrieval) as executor:
        futures = [executor.submit(_retrieve_single, claim, queries) for claim, queries in claim_queries.items()]
        for future in as_completed(futures):
            claim, evidences = future.result()
            evidence_dict[claim] = evidences
    
    return {"evidence": evidence_dict}

def verify_node(state: FactCheckState):
    """Phase 5: Verification - verify từng claim và tổng hợp kết luận toàn bài."""
    claim_evidence_dict = state["evidence"]
    verdicts = {}
    overall_verdict = {
        "factuality": "NEI",
        "summary": "Không đủ thông tin để kết luận toàn bộ bản tin.",
        "counts": {"true": 0, "false": 0, "nei": 0}
    }
    
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)

    verify_evidences_per_claim = max(1, int(os.getenv("VERIFY_EVIDENCES_PER_CLAIM", "1")))
    verify_max_retries = max(1, int(os.getenv("VERIFY_MAX_RETRIES", "1")))

    def _run_verify_once(claim: str, evidences_subset: list):
        nonlocal prompt_tokens, completion_tokens
        per_ev_chars = _adaptive_evidence_chars(len(evidences_subset))
        compact_subset = [_compact_evidence(ev, per_ev_chars) for ev in evidences_subset]
        original_doc_short = _build_verify_context(
            state.get("input_text", "") or "",
            claim,
        )
        evidence_text = "\n\n".join(
            [f"[Nguồn {i+1}]: {ev}" for i, ev in enumerate(compact_subset)]
        )
        
        user_input = prompt_config.verify_prompt.format(
            original_doc=state["input_text"],
            claim=claim,
            evidence=evidence_text,
        ).strip()

        verification_result = None
        for i in range(verify_max_retries):
            try:
                response = llm.invoke(verify_prompt)
                cleaned_content = clean_json_response(response.content)
                verification_result = json.loads(cleaned_content)

                if hasattr(response, 'response_metadata') and response.response_metadata:
                    usage = response.response_metadata.get('token_usage', {})
                    prompt_tokens += usage.get('prompt_tokens', 0)
                    completion_tokens += usage.get('completion_tokens', 0)

                if isinstance(verification_result, dict) and "factuality" in verification_result:
                    break
            except Exception as e:
                print(f"Verification error for claim '{claim}' (attempt {i+1}): {e}")
                continue

        if not isinstance(verification_result, dict):
            verification_result = {
                "reasoning": "Không đủ dữ liệu để xác nhận mệnh đề.",
                "error": "Thiếu căn cứ xác minh",
                "correction": "Chưa thể kết luận mệnh đề này là đúng.",
                "factuality": False,
            }

        verification_result.setdefault("reasoning", "Không có giải thích.")
        verification_result.setdefault("error", "không có")
        verification_result.setdefault("correction", "không có")
        verification_result["factuality"] = _normalize_factuality(
            verification_result.get("factuality", "NEI")
        )
        return verification_result
    
    for claim, evidences in claim_evidence_dict.items():
        if not evidences:
            verdicts[claim] = {
                "factuality": False,
                "reasoning": "Không tìm thấy đủ bằng chứng để xác nhận mệnh đề.",
                "error": "Thiếu căn cứ xác minh",
                "correction": "Chưa thể kết luận mệnh đề này là đúng."
            }
            continue

        first_pass = evidences[:verify_evidences_per_claim]
        verification_result = _run_verify_once(claim, first_pass)

        verdicts[claim] = verification_result

    # Deterministic fallback counts to keep article conclusion stable.
    true_count = 0
    false_count = 0
    for item in verdicts.values():
        factuality = _normalize_factuality(item.get("factuality", "NEI"))
        if factuality is True:
            true_count += 1
        else:
            false_count += 1

    if false_count > 0:
        deterministic_article = False
        deterministic_summary = "Bản tin có ít nhất một mệnh đề sai hoặc không đủ căn cứ để xác nhận."
    elif true_count > 0:
        deterministic_article = True
        deterministic_summary = "Các mệnh đề kiểm chứng đều đúng theo bằng chứng hiện có."
    else:
        deterministic_article = False
        deterministic_summary = "Không đủ căn cứ để xác nhận bản tin là đúng."

    # Prefer deterministic article verdict for consistency.
    overall_verdict["factuality"] = deterministic_article
    overall_verdict["summary"] = deterministic_summary
    overall_verdict["counts"] = {
        "true": true_count,
        "false": false_count,
        "nei": 0
    }
    
    return {
        "verdicts": verdicts,
        "overall_verdict": overall_verdict,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }
