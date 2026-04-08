import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import get_deepseek_llm, get_gemini_llm
from config.prompts_config import prompt_config
from tools.serper_api import search_google
from pipeline.state import FactCheckState
import json
import re
from datetime import datetime, timedelta

deepseek_llm = get_deepseek_llm()
gemini_llm = get_gemini_llm()


def _extract_token_usage(response) -> tuple[int, int]:
    """Return (prompt_tokens, completion_tokens) across providers."""
    prompt_tokens = 0
    completion_tokens = 0

    # Gemini/LangChain pattern
    usage_metadata = getattr(response, "usage_metadata", None)
    if isinstance(usage_metadata, dict):
        prompt_tokens += int(usage_metadata.get("input_tokens", 0) or 0)
        completion_tokens += int(usage_metadata.get("output_tokens", 0) or 0)

    # OpenAI/DeepSeek-compatible pattern
    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage", {}) or {}
        prompt_tokens += int(token_usage.get("prompt_tokens", 0) or 0)
        completion_tokens += int(token_usage.get("completion_tokens", 0) or 0)

    return prompt_tokens, completion_tokens


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

def _content_to_text(content) -> str:
    """Normalize LLM content into plain text for downstream JSON parsing."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text is not None:
                    parts.append(str(text))
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p).strip()

    if getattr(content, "content", None) is not None:
        # LangChain specific extraction
        lc_content = getattr(content, "content", "")
        if isinstance(lc_content, str):
            return lc_content
        elif isinstance(lc_content, list):
            parts = []
            for item in lc_content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if text is not None:
                        parts.append(str(text))
            return "\n".join(p for p in parts if p).strip()

    if isinstance(content, dict):
        text = content.get("text")
        if text is not None:
            return str(text)
        return json.dumps(content, ensure_ascii=False)

    return str(content or "")


def clean_json_response(content) -> str:
    """Clean LLM response để parse JSON
    
    LLM có thể trả về:
    - Markdown fence: ```json {...} ```
    - Text thừa trước/sau JSON
    - Single quotes thay vì double quotes
    """
    content = _content_to_text(content).strip()
    
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
    # Get current datetime for temporal context
    current_datetime = datetime.fromisoformat(state.get("current_datetime", datetime.now().isoformat()))
    current_date = current_datetime.date()
    
    max_claims = max(1, int(os.getenv("MAX_CLAIMS", "3")))
    
    user_input = prompt_config.decompose_prompt.format(
        doc=state["input_text"],
        max_claims=max_claims,
        current_date=current_date.strftime('%d/%m/%Y'),
    ).strip()
    
    deepseek_prompt_tokens = state.get("deepseek_prompt_tokens", 0)
    deepseek_completion_tokens = state.get("deepseek_completion_tokens", 0)
    gemini_prompt_tokens = state.get("gemini_prompt_tokens", 0)
    gemini_completion_tokens = state.get("gemini_completion_tokens", 0)
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    decompose_max_retries = max(1, int(os.getenv("DECOMPOSE_MAX_RETRIES", "1")))

    # Try to get valid claims
    claims = []
    
    for i in range(decompose_max_retries):
        try:
            response = gemini_llm.invoke(user_input)
            cleaned_content = clean_json_response(response.content)
            result = json.loads(cleaned_content)
            claims = result.get("claims", [])
            
            # Track tokens across Gemini/OpenAI-compatible metadata
            used_prompt_tokens, used_completion_tokens = _extract_token_usage(response)
            prompt_tokens += used_prompt_tokens
            completion_tokens += used_completion_tokens
            gemini_prompt_tokens += used_prompt_tokens
            gemini_completion_tokens += used_completion_tokens
            
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
    
    print(f"\n📄 DECOMPOSE NODE")
    print(f"  Extracted {len(claims)} claims")
    for i, claim in enumerate(claims, 1):
        print(f"  [{i}] {claim}")

    return {
        "claims": claims, 
        "retry_count": 0,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "deepseek_prompt_tokens": deepseek_prompt_tokens,
        "deepseek_completion_tokens": deepseek_completion_tokens,
        "gemini_prompt_tokens": gemini_prompt_tokens,
        "gemini_completion_tokens": gemini_completion_tokens,
        "current_datetime": state.get("current_datetime", datetime.now().isoformat()),
    }

def checkworthy_node(state: FactCheckState):
    """Phase 2: Checkworthy - Lọc các mệnh đề đáng kiểm chứng"""
    claims = state["claims"]
    print(f"\n📋 CHECKWORTHY NODE")
    print(f"  Input claims count: {len(claims)}")
    for i, claim in enumerate(claims, 1):
        print(f"  [{i}] {claim}")

    max_claims = max(1, int(os.getenv("MAX_CLAIMS", "3")))
    deepseek_prompt_tokens = state.get("deepseek_prompt_tokens", 0)
    deepseek_completion_tokens = state.get("deepseek_completion_tokens", 0)
    gemini_prompt_tokens = state.get("gemini_prompt_tokens", 0)
    gemini_completion_tokens = state.get("gemini_completion_tokens", 0)
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
            "completion_tokens": completion_tokens,
            "deepseek_prompt_tokens": deepseek_prompt_tokens,
            "deepseek_completion_tokens": deepseek_completion_tokens,
            "gemini_prompt_tokens": gemini_prompt_tokens,
            "gemini_completion_tokens": gemini_completion_tokens,
            "current_datetime": state.get("current_datetime", datetime.now().isoformat()),
        }

    user_input = prompt_config.checkworthy_prompt.format(texts="\n".join(candidate_claims)).strip()
    llm_result = None

    for i in range(checkworthy_max_retries):
        try:
            response = deepseek_llm.invoke(user_input)
            cleaned_content = clean_json_response(response.content)
            parsed = json.loads(cleaned_content)
            if isinstance(parsed, dict):
                llm_result = parsed

            used_prompt_tokens, used_completion_tokens = _extract_token_usage(response)
            prompt_tokens += used_prompt_tokens
            completion_tokens += used_completion_tokens
            deepseek_prompt_tokens += used_prompt_tokens
            deepseek_completion_tokens += used_completion_tokens

            if llm_result is not None:
                break
        except Exception as e:
            print(f"Checkworthy parse error (attempt {i+1}): {e}")
            continue

    checkworthy_claims = []
    if isinstance(llm_result, dict):
        # Chuẩn hóa keys từ LLM để tránh lỗi unmatch do dấu nháy, khoảng trắng (VD: ngoặc kép tên phim)
        normalized_llm_result = {
            re.sub(r'[\W_]+', '', k).lower(): v 
            for k, v in llm_result.items()
        }
        
        for claim in candidate_claims:
            norm_claim = re.sub(r'[\W_]+', '', claim).lower()
            verdict = str(normalized_llm_result.get(norm_claim, "")).strip().lower()
            
            # Fallback for partial/truncated keys from LLM 
            if not verdict:
                for k, v in normalized_llm_result.items():
                    if k in norm_claim or norm_claim in k:
                        verdict = str(v).strip().lower()
                        break

            print(f"  Verdict for '{claim[:50]}...': '{verdict}'")
            if verdict.startswith("có") or verdict.startswith("co"):
                checkworthy_claims.append(claim)
                print(f"    ✅ INCLUDED")
            else:
                print(f"    ❌ EXCLUDED")

    # Safe fallback if LLM output is empty/unparseable.
    if not checkworthy_claims:
        print(f"  ⚠️ No checkworthy claims found. Using fallback: all {len(candidate_claims)} claims")
        checkworthy_claims = candidate_claims
    
    print(f"  Output checkworthy claims count: {len(checkworthy_claims)}")
    for i, claim in enumerate(checkworthy_claims, 1):
        print(f"  [{i}] {claim}")

    return {
        "checkworthy_claims": checkworthy_claims,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "deepseek_prompt_tokens": deepseek_prompt_tokens,
        "deepseek_completion_tokens": deepseek_completion_tokens,
        "gemini_prompt_tokens": gemini_prompt_tokens,
        "gemini_completion_tokens": gemini_completion_tokens,
        "current_datetime": state.get("current_datetime", datetime.now().isoformat()),
    }

def retrieve_node(state: FactCheckState):
    """Phase 4: Evidence Retrieval - Serper only for lower latency."""
    claim_queries = state.get("queries", {})
    if not claim_queries:
        base_claims = state.get("checkworthy_claims") or state.get("claims", [])
        claim_queries = {claim: [claim] for claim in base_claims}
    
    print(f"\n🔎 RETRIEVE NODE")
    print(f"  Received {len(claim_queries)} claims to search")
    for i, claim in enumerate(claim_queries.keys(), 1):
        print(f"  [{i}] {claim[:60]}...")

    evidence_dict = {}
    retry_count = state.get("retry_count", 0)

    serper_top_k = int(os.getenv("SERPER_TOP_K", "3"))
    max_evidences_per_claim = int(os.getenv("MAX_EVIDENCES_PER_CLAIM", "3"))
    
    max_parallel_retrieval = max(1, int(os.getenv("MAX_PARALLEL_RETRIEVAL", "3")))

    def _retrieve_single(claim, queries):
        claim_evidences = []
        primary_query = queries[0] if queries else claim
        
        # Append current year to query to surface recent information
        current_datetime = datetime.fromisoformat(state.get("current_datetime", datetime.now().isoformat()))
        current_year = current_datetime.year
        
        # Only append year if there are no numbers indicating a specific year in the query
        if not re.search(r'\b(19|20)\d{2}\b', primary_query):
            search_query = f"{primary_query} hiện nay {current_year}"
        else:
            search_query = primary_query

        print(f"\n🔍 Đang tìm kiếm bằng chứng cho: '{claim[:50]}...' với query: '{search_query}'")

        serper_results = search_google(search_query, top_k=serper_top_k)
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
    
    print(f"\n  Completed searches for: {len(evidence_dict)} claims")
    for claim, evidences in evidence_dict.items():
        print(f"  - '{claim[:50]}...': {len(evidences)} evidence items")
    
    if evidence_dict and all(not ev for ev in evidence_dict.values()):
        retry_count += 1

    return {
        "evidence": evidence_dict,
        "retry_count": retry_count,
        "prompt_tokens": state.get("prompt_tokens", 0),
        "completion_tokens": state.get("completion_tokens", 0),
        "deepseek_prompt_tokens": state.get("deepseek_prompt_tokens", 0),
        "deepseek_completion_tokens": state.get("deepseek_completion_tokens", 0),
        "gemini_prompt_tokens": state.get("gemini_prompt_tokens", 0),
        "gemini_completion_tokens": state.get("gemini_completion_tokens", 0),
        "current_datetime": state.get("current_datetime", datetime.now().isoformat()),
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
    
    gemini_prompt_tokens = state.get("gemini_prompt_tokens", 0)
    gemini_completion_tokens = state.get("gemini_completion_tokens", 0)
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)

    verify_evidences_per_claim = max(1, int(os.getenv("VERIFY_EVIDENCES_PER_CLAIM", "3")))
    verify_max_retries = max(1, int(os.getenv("VERIFY_MAX_RETRIES", "1")))

    def _run_verify_once(claim: str, evidences_subset: list):
        used_p_tokens = 0
        used_c_tokens = 0
        
        original_doc_short = _build_verify_context(
            state.get("input_text", "") or "",
            claim,
        )
        evidence_text = "\n\n".join(
            [f"[Nguồn {i+1}]: {_evidence_to_text(ev)}" for i, ev in enumerate(evidences_subset) if _evidence_to_text(ev)]
        )
        
        current_datetime = datetime.fromisoformat(state.get("current_datetime", datetime.now().isoformat()))
        current_year = current_datetime.year
        
        verify_prompt = prompt_config.verify_prompt.format(
            original_doc=original_doc_short,
            claim=claim,
            evidence=evidence_text,
            current_year=current_year
        ).strip()

        verification_result = None
        for i in range(verify_max_retries):
            try:
                # Trích xuất nội dung text ra trước nếu LangChain trả về mảng dict
                raw_response = gemini_llm.invoke(verify_prompt)
                
                content_text = _content_to_text(raw_response.content if hasattr(raw_response, 'content') else raw_response)
                
                cleaned_content = clean_json_response(content_text)
                
                verification_result = json.loads(cleaned_content)

                _p_tokens, _c_tokens = _extract_token_usage(raw_response)
                used_p_tokens += _p_tokens
                used_c_tokens += _c_tokens

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
        return verification_result, used_p_tokens, used_c_tokens
    
    # CHẠY XÁC MINH SONG SONG KẾT HỢP XỬ LÝ LỖI
    max_parallel_verify = max(1, int(os.getenv("MAX_PARALLEL_VERIFY", "3")))
    
    def _verify_wrapper(claim: str, evidences: list):
        if not evidences:
            return claim, {
                "factuality": False,
                "reasoning": "Không tìm thấy đủ bằng chứng để xác nhận mệnh đề.",
                "error": "Thiếu căn cứ xác minh",
                "correction": "Chưa thể kết luận mệnh đề này là đúng."
            }, 0, 0

        first_pass = evidences[:verify_evidences_per_claim]
        verdict, p_tok, c_tok = _run_verify_once(claim, first_pass)
        
        # Check if any unverified evidence sources are used
        has_unverified = any(ev.get("tier") == "unverified" for ev in first_pass if isinstance(ev, dict))
        if has_unverified:
            verdict["unverified_sources_used"] = True
            
        return claim, verdict, p_tok, c_tok

    with ThreadPoolExecutor(max_workers=max_parallel_verify) as executor:
        futures = {
            executor.submit(_verify_wrapper, claim, evidences): claim 
            for claim, evidences in claim_evidence_dict.items()
        }
        for future in as_completed(futures):
            try:
                claim, result, p_tok, c_tok = future.result()
                verdicts[claim] = result
                prompt_tokens += p_tok
                completion_tokens += c_tok
                gemini_prompt_tokens += p_tok
                gemini_completion_tokens += c_tok
            except Exception as e:
                print(f"Error executing verification wrapper: {e}")

    # Deterministic fallback counts to keep article conclusion stable.
    true_count = 0
    false_count = 0
    nei_count = 0
    unverified_claims_count = 0
    for item in verdicts.values():
        if item.get("unverified_sources_used"):
            unverified_claims_count += 1
            if "reasoning" in item:
                item["reasoning"] += " (Chú ý: Kết luận này bao gồm nguồn chưa được kiểm duyệt)."
                
        error = item.get("error", "").lower()
        # If error is "unverified sources only", classify as NEI
        if error == "unverified sources only":
            nei_count += 1
        else:
            factuality = _normalize_factuality(item.get("factuality", "NEI"))
            if factuality is True:
                true_count += 1
            else:
                false_count += 1

    if false_count > 0:
        deterministic_article = False
        deterministic_summary = "Bản tin có ít nhất một mệnh đề sai hoặc không đủ căn cứ xác thực."
    elif true_count > 0:
        deterministic_article = True
        deterministic_summary = "Các mệnh đề kiểm chứng đều đúng theo bằng chứng xác thực."
    else:
        deterministic_article = False
        if nei_count > 0:
            deterministic_summary = "Không đủ nguồn bằng chứng xác thực để kết luận."
        else:
            deterministic_summary = "Không đủ căn cứ để xác nhận bản tin là đúng."
            
    if unverified_claims_count > 0:
        deterministic_summary += f" (Chú thích: Có {unverified_claims_count} mệnh đề được đối chiếu với nguồn thông tin chưa qua kiểm duyệt)."

    # Prefer deterministic article verdict for consistency.
    overall_verdict["factuality"] = deterministic_article
    overall_verdict["summary"] = deterministic_summary
    overall_verdict["counts"] = {
        "true": true_count,
        "false": false_count,
        "nei": nei_count
    }
    
    return {
        "verdicts": verdicts,
        "overall_verdict": overall_verdict,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "gemini_prompt_tokens": gemini_prompt_tokens,
        "gemini_completion_tokens": gemini_completion_tokens,
        "current_datetime": state.get("current_datetime", datetime.now().isoformat()),
    }
