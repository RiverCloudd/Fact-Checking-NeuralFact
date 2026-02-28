from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core.config import get_llm
from config.prompts_config import prompt_config
from tools.serper_api import search_google
from tools.qdrant_db import search_qdrant
from pipeline.state import FactCheckState
import json
import re

llm = get_llm()

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
    user_input = prompt_config.decompose_prompt.format(doc=state["input_text"]).strip()
    
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    
    # Try up to 3 times to get valid claims
    claims = []
    for i in range(3):
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
    
    # Format claims with numbers
    joint_texts = "\n".join([f"{i + 1}. {claim}" for i, claim in enumerate(claims)])
    user_input = prompt_config.checkworthy_prompt.format(texts=joint_texts)
    
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    
    checkworthy_claims = claims  # Default: assume all are checkworthy
    claim2checkworthy = {}
    
    # Try up to 3 times
    for i in range(3):
        try:
            response = llm.invoke(user_input)
            cleaned_content = clean_json_response(response.content)
            claim2checkworthy = json.loads(cleaned_content)
            
            # Track tokens
            if hasattr(response, 'response_metadata') and response.response_metadata:
                usage = response.response_metadata.get('token_usage', {})
                prompt_tokens += usage.get('prompt_tokens', 0)
                completion_tokens += usage.get('completion_tokens', 0)
            
            # Filter claims that start with "Có" (Yes)
            valid_answer = list(
                filter(
                    lambda x: x[1].startswith("Có") or x[1].startswith("Không"),
                    claim2checkworthy.items(),
                )
            )
            checkworthy_claims = list(
                filter(
                    lambda x: x[1].startswith("Có"), 
                    claim2checkworthy.items()
                )
            )
            checkworthy_claims = [x[0] for x in checkworthy_claims]
            
            if len(valid_answer) == len(claim2checkworthy):
                break
        except Exception as e:
            print(f"Checkworthy error (attempt {i+1}): {e}")
            if 'response' in locals():
                print(f"Raw response: {response.content[:300]}...")
            continue
    
    return {
        "checkworthy_claims": checkworthy_claims,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

def query_gen_node(state: FactCheckState):
    """Phase 3: Query Generation - Tạo nhiều câu hỏi kiểm chứng cho mỗi mệnh đề"""
    claims = state["checkworthy_claims"]
    max_queries_per_claim = 5
    
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    
    claim_queries = {}
    
    # Generate queries for each claim
    for claim in claims:
        user_input = prompt_config.qgen_prompt.format(claim=claim)
        
        generated_questions = []
        # Try up to 3 times
        for i in range(3):
            try:
                response = llm.invoke(user_input)
                cleaned_content = clean_json_response(response.content)
                result = json.loads(cleaned_content)
                generated_questions = result.get("Questions", [])
                
                # Track tokens
                if hasattr(response, 'response_metadata') and response.response_metadata:
                    usage = response.response_metadata.get('token_usage', {})
                    prompt_tokens += usage.get('prompt_tokens', 0)
                    completion_tokens += usage.get('completion_tokens', 0)
                
                if isinstance(generated_questions, list) and len(generated_questions) > 0:
                    break
            except Exception as e:
                print(f"Query generation error for claim '{claim}' (attempt {i+1}): {e}")
                if 'response' in locals():
                    print(f"Raw response: {response.content[:200]}...")
                continue
        
        # Always include the original claim as the first query
        # Then add generated questions up to max_queries_per_claim - 1
        queries = [claim] + generated_questions[:(max_queries_per_claim - 1)]
        claim_queries[claim] = queries
    
    return {
        "queries": claim_queries,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

def retrieve_node(state: FactCheckState):
    """Phase 4: Evidence Retrieval - Hybrid: Qdrant Vector DB (Priority) fallback to Serper API"""
    claim_queries = state["queries"]
    evidence_dict = {}
    
    # Ngưỡng RRF quyết định bằng chứng Local có đủ xịn không (Dựa trên hệ điểm mới 1.0, 0.66, 0.25...)
    QDRANT_SCORE_THRESHOLD = 0.70 
    top_k = 3
    
    for claim, queries in claim_queries.items():
        claim_evidences = []
        is_evidence_strong = False # Cờ kiểm soát
        
        print(f"\n🔍 Đang tìm kiếm bằng chứng cho: '{claim[:50]}...'")
        
        # BƯỚC 1: Quét qua thư viện Qdrant trước
        for query in queries:
            qdrant_results = search_qdrant(query, top_k=2)
            
            if qdrant_results:
                claim_evidences.extend(qdrant_results)
                
                # Bóc tách điểm số từ chuỗi trả về của Top 1 (VD: "... (score: 1.000)")
                first_result = qdrant_results[0]
                match = re.search(r'\(score:\s*([0-9.]+)\)', first_result)
                
                if match:
                    max_score = float(match.group(1))
                    
                    if max_score >= QDRANT_SCORE_THRESHOLD:
                        is_evidence_strong = True
                        print(f"  ✅ Tóm được bằng chứng Local chất lượng cao (Score: {max_score:.3f}). Bỏ qua Google Search.")
                        break # Dừng vòng lặp query, không cần tìm thêm trong Qdrant cho claim này nữa
        
        # BƯỚC 2: Rẽ nhánh - Có gọi Serper hay không?
        if not is_evidence_strong:
            print(f"  ⚠️ Không có bằng chứng Local tốt. Kích hoạt Serper Google Search...")
            
            # Mẹo tối ưu: Chỉ dùng câu Claim gốc (câu đầu tiên trong mảng) để Search Google.
            # Không spam cả 5 câu query lên Google để tiết kiệm Token API và thời gian.
            original_claim = queries[0] 
            serper_results = search_google(original_claim, top_k=top_k)
            
            if serper_results:
                claim_evidences.extend(serper_results)
                print(f"  🌐 Đã bổ sung {len(serper_results)} bằng chứng từ Google.")
            else:
                print("  ❌ Google cũng không có thông tin rõ ràng.")
        
        # BƯỚC 3: Lọc trùng lặp (Deduplicate)
        unique_evidences = list(set(claim_evidences))
        evidence_dict[claim] = unique_evidences
    
    return {"evidence": evidence_dict}

def verify_node(state: FactCheckState):
    """Phase 5: Verification - Kiểm chứng với error detection và correction"""
    claim_evidence_dict = state["evidence"]
    verdicts = {}
    
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    
    # Verify each claim against all its evidences
    for claim, evidences in claim_evidence_dict.items():
        if not evidences:
            verdicts[claim] = {
                "factuality": "NEI",
                "reasoning": "Không tìm thấy bằng chứng.",
                "error": "không có",
                "correction": "không có"
            }
            continue
        
        # Combine evidences into a single text
        evidence_text = "\n\n".join(
            [f"[Nguồn {i+1}]: {ev}" for i, ev in enumerate(evidences[:5])]  # Limit to top 5
        )
        
        user_input = prompt_config.verify_prompt.format(
            claim=claim,
            evidence=evidence_text
        )
        
        # Try up to 3 times
        verification_result = None
        for i in range(3):
            try:
                response = llm.invoke(user_input)
                cleaned_content = clean_json_response(response.content)
                verification_result = json.loads(cleaned_content)
                
                # Track tokens
                if hasattr(response, 'response_metadata') and response.response_metadata:
                    usage = response.response_metadata.get('token_usage', {})
                    prompt_tokens += usage.get('prompt_tokens', 0)
                    completion_tokens += usage.get('completion_tokens', 0)
                
                # Validate required keys
                if all(k in verification_result for k in ["reasoning", "factuality"]):
                    break
            except Exception as e:
                print(f"Verification error for claim '{claim}' (attempt {i+1}): {e}")
                if 'response' in locals():
                    print(f"Raw response: {response.content[:300]}...")
                continue
        
        # Default if failed
        if verification_result is None:
            verification_result = {
                "reasoning": "[Cảnh báo] Không thể xác định tính chính xác của mệnh đề.",
                "factuality": False,
                "error": "Không xác định được",
                "correction": "không có"
            }
        
        verdicts[claim] = verification_result
    
    return {
        "verdicts": verdicts,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }
