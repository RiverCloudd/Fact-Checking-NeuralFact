import os
import argparse

def check_continuos_tuples(tuples_list):
    # Check if the list of tuples is continuous, meaning that the end of one tuple is one lower than the start of the next tuple.
    if not tuples_list:
        return True
    sorted_tuples = sorted(tuples_list, key=lambda x: x[0])
    for i in range(len(sorted_tuples) - 1):
        if sorted_tuples[i][1] + 1 != sorted_tuples[i + 1][0]:
            return False
    return True

def merge_jsonl_files(folder_dir, output_file):
    # Merges all JSONL files in the specified folder into a single JSONL file.
    # Assume all jsonl files in the folder has same name inititals, and all end with _x-y.jsonl where x and y are integers.
    jsonl_files = [f for f in os.listdir(folder_dir) if f.endswith('.jsonl')]
    if not jsonl_files:
        print("No JSONL files found in the specified folder.")
        return
    
    tuples_list = []
    for file in jsonl_files:
        name_part = file.split('.')[0]  # Get the part before .jsonl
        range_part = name_part.split('_')[-1]  # Get the part after the last underscore
        x, y = map(int, range_part.split('-'))  # Split by '-' and convert to integers
        tuples_list.append((x, y))
        
    if not check_continuos_tuples(tuples_list):
        print("The JSONL files are not continuous. Please check file names or missing files.")
        return
    
    # If no output file specified, derive from the initial part of the first file's name
    if output_file is None:
        first_file = sorted(jsonl_files, key=lambda f: int(f.split('_')[-1].split('-')[0]))[0]
        # Get everything before the last _x-y range part
        name_part = first_file.split('.')[0]
        parts = name_part.split('_')
        initial = '_'.join(parts[:-1])  # Everything except the range part
        output_file = f"{initial}.jsonl"
    
    # Check line counts against expected ranges
    for file in jsonl_files:
        name_part = file.split('.')[0]
        range_part = name_part.split('_')[-1]
        x, y = map(int, range_part.split('-'))
        expected_count = y - x + 1
        with open(os.path.join(folder_dir, file), 'r', encoding='utf-8') as f:
            actual_count = sum(1 for line in f if line.strip())
        if actual_count != expected_count:
            print(f"WARNING: {file} has {actual_count} lines but expected {expected_count} (range {x}-{y}).")
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file in sorted(jsonl_files, key=lambda f: int(f.split('_')[-1].split('-')[0])):  # Sort files based on the starting number
            with open(os.path.join(folder_dir, file), 'r', encoding='utf-8') as infile:
                for line in infile:
                    outfile.write(line)
    
    print(f"Successfully merged {len(jsonl_files)} JSONL files into {output_file}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge multiple JSONL files into a single JSONL file.")
    parser.add_argument("--folder", required=True, help="Input folder containing target JSONL files.")
    parser.add_argument("--output", default=None, help="Name of the output file. If not provided, derived from the common initial of input file names.")
    args = parser.parse_args()
    
    merge_jsonl_files(args.folder, args.output)