import os

import pandas as pd
import time
import argparse
import json
from datetime import datetime
from tqdm import tqdm

# Import pipeline components
import pipeline.nodes
from pipeline.graph import factcheck_app
from core.config import (
    DEEPSEEK_PRICE_1M_INPUT_TOKENS, DEEPSEEK_PRICE_1M_OUTPUT_TOKENS,
    GEMINI_PRICE_1M_INPUT_TOKENS, GEMINI_PRICE_1M_OUTPUT_TOKENS
)


def test_claims(csv_path, output_csv, limit=None, frac=None):
    df = pd.read_csv(csv_path)
    if frac:
        df = df.sample(frac=frac, random_state=42)
    elif limit:
        df = df.head(limit)
    
    csv_results = []
    print_results = []
    correct_count = 0
    total_count = 0
    
    # Token usage tracking
    deepseek_tokens = {"p": 0, "c": 0}
    gemini_tokens = {"p": 0, "c": 0}  # vẫn giữ nếu pipeline có dùng
    
    print(f"Bắt đầu kiểm thử {len(df)} mệnh đề...")
    start_total_time = time.time()
    
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        claim_id = row['id']
        claim_text = row['claim']
        
        label_val = str(row['label']).strip().lower()
        if label_val in ['true', '1', 't']:
            true_label = "true"
        elif label_val in ['false', '0', 'f']:
            true_label = "false"
        else:
            true_label = "nei"
        
        initial_state = {
            "input_text": claim_text,
            "claims": [],
            "checkworthy_claims": [],
            "queries": {},
            "evidence": {},
            "verdicts": {},
            "overall_verdict": {},
            "retry_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "deepseek_prompt_tokens": 0,
            "deepseek_completion_tokens": 0,
            "gemini_prompt_tokens": 0,
            "gemini_completion_tokens": 0,
            "current_datetime": datetime.now().isoformat()
        }
        
        start_claim_time = time.time()
        
        try:
            final_state = factcheck_app.invoke(initial_state)
            
            overall_verdict = final_state.get("overall_verdict", {})
            factuality = overall_verdict.get("factuality")
            agent_summary = overall_verdict.get("summary", "No summary found")
            
            if factuality is not None:
                predicted_label = "true" if factuality else "false"
            else:
                predicted_label = "true"
                for claim, v_data in final_state.get("verdicts", {}).items():
                    if str(v_data.get("factuality", "")).lower() in ["false", "refuted"]:
                        predicted_label = "false"
                        break
            
            # Lấy danh sách các nguồn (sources) từ evidence
            evidence_dict = final_state.get("evidence", {})
            sources_set = set()
            for claim_text, evidences in evidence_dict.items():
                for ev in evidences:
                    if isinstance(ev, dict) and ev.get("url"):
                        sources_set.add(str(ev.get("url")))
            sources_str = ", ".join(sources_set) if sources_set else ""

            # Token tracking
            deepseek_tokens["p"] += final_state.get("deepseek_prompt_tokens", 0)
            deepseek_tokens["c"] += final_state.get("deepseek_completion_tokens", 0)
            gemini_tokens["p"] += final_state.get("gemini_prompt_tokens", 0)
            gemini_tokens["c"] += final_state.get("gemini_completion_tokens", 0)
            
            is_correct = (predicted_label == true_label)
            if is_correct:
                correct_count += 1
            total_count += 1
            
            claim_time = time.time() - start_claim_time
            
            csv_results.append({
                "id": claim_id,
                "predicted_label": predicted_label,
                "summary": agent_summary,
                "sources": sources_str,
                "decompose": json.dumps(final_state.get("claims", []), ensure_ascii=False),
                "checkworthy": json.dumps(final_state.get("checkworthy_claims", []), ensure_ascii=False),
                "retrieve": json.dumps(final_state.get("evidence", {}), ensure_ascii=False),
                "verify": json.dumps(final_state.get("verdicts", {}), ensure_ascii=False)
            })
            
            print_results.append({
                "ID": claim_id,
                "Expected": true_label.capitalize(),
                "Answer": predicted_label.capitalize(),
                "Is_True": is_correct,
                "Time(s)": round(claim_time, 1),
                "Reason": agent_summary[:50] + "..." if len(agent_summary) > 50 else agent_summary,
                "Sources": sources_str
            })
            
        except Exception as e:
            claim_time = time.time() - start_claim_time
            print(f"\n❌ Error processing claim {claim_id}: {e}")
            
            csv_results.append({
                "id": claim_id,
                "predicted_label": "error",
                "summary": str(e),
                "sources": "",
                "decompose": "",
                "checkworthy": "",
                "retrieve": "",
                "verify": ""
            })
            
            print_results.append({
                "ID": claim_id,
                "Expected": true_label.capitalize(),
                "Answer": "Error",
                "Is_True": False,
                "Time(s)": round(claim_time, 1),
                "Reason": "Pipeline Execution Error",
                "Sources": ""
            })
            
    end_total_time = time.time()
    execution_time = end_total_time - start_total_time
    execution_minutes = execution_time / 60
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
    
    # ✅ Cost chỉ dùng DeepSeek
    deepseek_cost = (
        deepseek_tokens["p"] * DEEPSEEK_PRICE_1M_INPUT_TOKENS +
        deepseek_tokens["c"] * DEEPSEEK_PRICE_1M_OUTPUT_TOKENS
    ) / 1_000_000
        
    gemini_cost = (
        gemini_tokens["p"] * GEMINI_PRICE_1M_INPUT_TOKENS +
        gemini_tokens["c"] * GEMINI_PRICE_1M_OUTPUT_TOKENS
    ) / 1_000_000
    
    total_cost = deepseek_cost + gemini_cost

    print("\n" + "="*80)
    print(f"BENCHMARK COMPLETE IN {execution_minutes:.2f} MINUTES")
    print(f"TOTAL EST. COST: ${total_cost:.4f} (DeepSeek: ${deepseek_cost:.4f}, Gemini: ${gemini_cost:.4f})")
    print(f"TOTAL TOKENS: {sum(deepseek_tokens.values()) + sum(gemini_tokens.values())}")
    print("="*80 + "\n")
    
    print_df = pd.DataFrame(print_results)
    if not print_df.empty:
        print(print_df.to_string(index=False))
        
        output_dir = os.path.dirname(output_csv)
        compare_result_path = os.path.join(output_dir, "compare_result.csv") if output_dir else "compare_result.csv"
        print_df.to_csv(compare_result_path, index=False, encoding='utf-8-sig')
        
        print(f"\nOVERALL ACCURACY: {accuracy:.1f}% ({correct_count}/{total_count})")
        print(f"Đã lưu kết quả so sánh tại: {compare_result_path}")
        
    print("="*80)
    
    results_df = pd.DataFrame(csv_results)
    results_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Đã lưu kết quả chi tiết với Summary tại: {output_csv}")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=r"../../data/fact_check_claims.csv")
    parser.add_argument("--output", type=str, default="test_results.csv")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--frac", type=float, default=None)
    args = parser.parse_args()
    
    test_claims(args.input, args.output, args.limit, args.frac)