import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import get_llm
from config.prompts_config import prompt_config
from tools.serper_api import search_google
from pipeline.state import FactCheckState
import json
import re

llm = get_llm()


def _evidence_to_text(item) -> str:
    if isinstance(item, dict):
        text = str(item.get("text", "")).strip()
        if text:
            return text

        title = str(item.get("title", "")).strip()
        snippet = str(item.get("snippet", "")).strip()
        url = str(item.get("url", "")).strip()

        parts = []
        if title:
            parts.append(f"[{title}]")
        if snippet:
            parts.append(snippet)
        if url:
            parts.append(f"Nguồn: {url}")
        return "\n".join(parts).strip()

    return str(item or "").strip()


def _evidence_key(item) -> str:
    if isinstance(item, dict):
        url = str(item.get("url", "")).strip()
        if url:
            return url
    return _evidence_to_text(item)


def _stable_dedupe(items):
    """Remove duplicates while preserving original order."""
    unique_items = []
    seen = set()
    for item in items:
        key = _evidence_key(item)
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


def _build_verify_context(input_text: str, claim: str) -> str:
    """Return the full original document context for verification."""
    del claim
    return re.sub(r"\s+", " ", (input_text or "")).strip()

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


def _split_sentences_vi(text: str) -> list[str]:
    """Fallback sentence splitter for Vietnamese without external NLP packages."""
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return []

    # Split by common sentence endings while keeping Vietnamese-friendly punctuation.
    parts = re.split(r"(?<=[\.\!\?…])\s+|\n+", normalized)
    sentences = [p.strip(" \t\r\n-•") for p in parts if p and p.strip()]

    if len(sentences) <= 1:
        return [normalized]
    return sentences

def decompose_node(state: FactCheckState):
    """Phase 1: Decompose - Phân tách văn bản thành các mệnh đề nguyên tử"""
    user_input = prompt_config.decompose_prompt.format(
        doc=state["input_text"],
        max_claims=max(1, int(os.getenv("MAX_CLAIMS", "3"))),
    ).strip()
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)

    max_claims = max(1, int(os.getenv("MAX_CLAIMS", "3")))
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
    
    # Fallback: split by sentences if LLM fails (no external tokenizer required)
    if not claims:
        sentences = _split_sentences_vi(state["input_text"])
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

    max_claims = max(1, int(os.getenv("MAX_CLAIMS", "3")))
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    checkworthy_max_retries = max(1, int(os.getenv("CHECKWORTHY_MAX_RETRIES", "1")))

    # Keep only clean candidate claims before sending to LLM.
    candidate_claims = [c.strip() for c in claims if isinstance(c, str) and c.strip()]
    candidate_claims = candidate_claims[:max_claims]

    if not candidate_claims:
        return {
            "checkworthy_claims": [],
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        }

    user_input = prompt_config.checkworthy_prompt.format(texts="\n".join(candidate_claims)).strip()
    llm_result = None

    for i in range(checkworthy_max_retries):
        try:
            response = llm.invoke(user_input)
            cleaned_content = clean_json_response(response.content)
            parsed = json.loads(cleaned_content)
            if isinstance(parsed, dict):
                llm_result = parsed

            if hasattr(response, 'response_metadata') and response.response_metadata:
                usage = response.response_metadata.get('token_usage', {})
                prompt_tokens += usage.get('prompt_tokens', 0)
                completion_tokens += usage.get('completion_tokens', 0)

            if llm_result is not None:
                break
        except Exception as e:
            print(f"Checkworthy parse error (attempt {i+1}): {e}")
            continue

    checkworthy_claims = []
    if isinstance(llm_result, dict):
        for claim in candidate_claims:
            verdict = str(llm_result.get(claim, "")).strip().lower()
            if verdict.startswith("có"):
                checkworthy_claims.append(claim)

    # Safe fallback if LLM output is empty/unparseable.
    if not checkworthy_claims:
        checkworthy_claims = candidate_claims

    return {
        "checkworthy_claims": checkworthy_claims,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

def retrieve_node(state: FactCheckState):
    """Phase 4: Evidence Retrieval - Serper only for lower latency."""
    claim_queries = state.get("queries", {})
    if not claim_queries:
        base_claims = state.get("checkworthy_claims") or state.get("claims", [])
        claim_queries = {claim: [claim] for claim in base_claims}

    evidence_dict = {}
    retry_count = state.get("retry_count", 0)

    serper_top_k = int(os.getenv("SERPER_TOP_K", "3"))
    max_evidences_per_claim = int(os.getenv("MAX_EVIDENCES_PER_CLAIM", "3"))
    
    max_parallel_retrieval = max(1, int(os.getenv("MAX_PARALLEL_RETRIEVAL", "3")))

    def _retrieve_single(claim, queries):
        claim_evidences = []
        primary_query = queries[0] if queries else claim
        
        print(f"\n🔍 Đang tìm kiếm bằng chứng cho: '{claim[:50]}...'")

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
    
    if evidence_dict and all(not ev for ev in evidence_dict.values()):
        retry_count += 1

    return {
        "evidence": evidence_dict,
        "retry_count": retry_count,
    }

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
        original_doc_short = _build_verify_context(
            state.get("input_text", "") or "",
            claim,
        )
        evidence_text = "\n\n".join(
            [f"[Nguồn {i+1}]: {_evidence_to_text(ev)}" for i, ev in enumerate(evidences_subset) if _evidence_to_text(ev)]
        )
        verify_prompt = prompt_config.verify_prompt.format(
            original_doc=original_doc_short,
            claim=claim,
            evidence=evidence_text,
        ).strip()

        # print(f"\n🧪 Verify prompt for claim: '{claim}'\n{verify_prompt}\n")

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
