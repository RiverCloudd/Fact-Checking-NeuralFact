import json
import argparse
from libretranslatepy import LibreTranslateAPI

# Initialize the API (point to your local server)
lt = LibreTranslateAPI("http://127.0.0.1:5000")

# Function to translate a string or list
def translate_text(text, source_lang="en", target_lang="vi"):
    if isinstance(text, list):
        return [lt.translate(item, source_lang, target_lang) for item in text]
    elif isinstance(text, str):
        return lt.translate(text, source_lang, target_lang)
    return text  # Leave non-strings unchanged

# Parse command line arguments
parser = argparse.ArgumentParser(description="Translate JSONL file lines from English to Vietnamese")
parser.add_argument("--start", type=int, required=True, help="Start line number (1-indexed)")
parser.add_argument("--end", type=int, required=True, help="End line number (1-indexed, inclusive)")
args = parser.parse_args()

# Validate arguments
if args.end < args.start:
    parser.error("--end must be equal to or greater than --start")

# Input and output files
input_file = "Factbench.jsonl"
output_file = f"tl-res/Factbench_vi_{args.start}-{args.end}.jsonl"

with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
    for line_num, line in enumerate(infile, start=1):
        # Skip lines outside the specified range
        if line_num < args.start:
            continue
        if line_num > args.end:
            break
        
        data = json.loads(line.strip())
        # Break when end of file is reached
        if not data:
            break
        
        print(f"Translating line {line_num}...")  # Progress indicator
        # Translate relevant fields (adjust based on your needs for accuracy)
        if "prompt" in data:
            data["prompt"] = translate_text(data["prompt"])
        if "response" in data:
            data["response"] = translate_text(data["response"])
        if "claims" in data:
            data["claims"] = translate_text(data["claims"])
        # Add more fields like "hallucination_spans" if needed
        
        # Write translated JSON line
        json.dump(data, outfile, ensure_ascii=False)
        outfile.write("\n")

print(f"Translation complete. Output saved to {output_file}")