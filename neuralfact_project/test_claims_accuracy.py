import pandas as pd
import time
import argparse
from tqdm import tqdm

from pipeline.graph import factcheck_app

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
    
    print(f"Bắt đầu kiểm thử {len(df)} mệnh đề...")
    start_total_time = time.time()
    
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        claim_id = row['id']
        claim_text = row['claim']
        
        # Determine strict true/false mapped true_label
        label_val = str(row['label']).strip().lower()
        if label_val in ['true', '1', 't']:
            true_label = "true"
        elif label_val in ['false', '0', 'f']:
            true_label = "false"
        else:
            true_label = "nei"
        
        initial_state = {
            "input_text": claim_text, "claims": [], "checkworthy_claims": [],
            "queries": {}, "evidence": {}, "verdicts": {}, "retry_count": 0,
            "prompt_tokens": 0, "completion_tokens": 0
        }
        
        start_claim_time = time.time()
        
        try:
            final_state = factcheck_app.invoke(initial_state)
            
            # Extract final factuality: nếu có 1 cái sai thì là sai, còn lại là đúng
            predicted_label = "true"
            for claim, verdict_data in final_state.get("verdicts", {}).items():
                fact = verdict_data.get("factuality", "nei")
                val = str(fact).strip().lower()
                if val in ["false", "refuted"]:
                    predicted_label = "false"
                    break
                
            is_correct = (predicted_label == true_label)
            if is_correct:
                correct_count += 1
            total_count += 1
            
            claim_time = time.time() - start_claim_time
            
            # File CSV chỉ lưu id và kết quả true/false
            csv_results.append({
                "id": claim_id,
                "predicted_label": predicted_label
            })
            
            # Lưu dữ liệu in ra bảng thống kê
            print_results.append({
                "ID": claim_id,
                "Expected": true_label.capitalize(),
                "Answer": predicted_label.capitalize(),
                "Is_True": is_correct,
                "Time_Taken(s)": round(claim_time, 1)
            })
            
        except Exception as e:
            # error case
            claim_time = time.time() - start_claim_time
            
            csv_results.append({
                "id": claim_id,
                "predicted_label": "error"
            })
            
            print_results.append({
                "ID": claim_id,
                "Expected": true_label.capitalize(),
                "Answer": "Error",
                "Is_True": False,
                "Time_Taken(s)": round(claim_time, 1)
            })
            
    end_total_time = time.time()
    execution_time = end_total_time - start_total_time
    execution_minutes = execution_time / 60
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
    
    print("\n" + "="*80)
    print(f"BENCHMARK COMPLETE IN {execution_minutes:.2f} MINUTES")
    print("="*80 + "\n")
    
    print_df = pd.DataFrame(print_results)
    if not print_df.empty:
        # In ra như bảng trong hình ảnh yêu cầu
        print(print_df.to_string())
        
    print(f"\nOVERALL ACCURACY: {accuracy:.1f}% ({correct_count}/{total_count})")
    print("="*80)
    
    results_df = pd.DataFrame(csv_results)
    results_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Đã lưu kết quả chi tiết tại: {output_csv}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test claims from a CSV using the NeuralFact pipeline.")
    parser.add_argument("--input", type=str, default=r"d:\Nam4\UDPTDLTM\Project\myself\data\fact_check_claims.csv", help="Path to the input CSV file.")
    parser.add_argument("--output", type=str, default="test_results.csv", help="Path to save the output CSV file.")
    parser.add_argument("--limit", type=int, default=None, help="Number of claims to test (default: all).")
    parser.add_argument("--frac", type=float, default=None, help="Fraction of claims to test randomly (e.g., 0.1 for 10%).")
    args = parser.parse_args()
    
    test_claims(args.input, args.output, args.limit, args.frac)
