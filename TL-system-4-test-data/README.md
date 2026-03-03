# TLSystem4TestData

A toolset for translating JSONL datasets from English to Vietnamese using [LibreTranslate](https://github.com/LibreTranslate/LibreTranslate), and merging the translated chunks back into a single file.

## Prerequisites

- Python 3.8+
- A running [LibreTranslate](https://github.com/LibreTranslate/LibreTranslate) server on `http://127.0.0.1:5000`

## Installation

1. Navigate to the project directory.

2. Install dependencies:

```sh
pip install -r requirements.txt
```

3. Start a local LibreTranslate server (in a separate terminal):

```sh
libretranslate
```

The server will start on `http://127.0.0.1:5000` by default.

## Usage

### 1. Translate JSONL lines

Use [`translate_jsonl.py`](translate_jsonl.py) to translate a range of lines from [`Factbench.jsonl`](Factbench.jsonl) (English) to Vietnamese. The output is saved to the [`tl-res/`](tl-res/) folder.

```sh
python translate_jsonl.py --start <START_LINE> --end <END_LINE>
```

**Arguments:**

| Argument  | Description                                  |
|-----------|----------------------------------------------|
| `--start` | Start line number (1-indexed)                |
| `--end`   | End line number (1-indexed, inclusive)        |

**Example** — translate lines 1 through 10:

```sh
python translate_jsonl.py --start 1 --end 10
```

This produces `tl-res/Factbench_vi_1-10.jsonl`.

> **Note:** `--end` must be greater than or equal to `--start`. You can translate the file in multiple batches by running the script with different ranges.

### 2. Merge translated files

Once all chunks are translated, use [`merge_jsonl.py`](merge_jsonl.py) to merge them into a single JSONL file.

```sh
python merge_jsonl.py --folder <FOLDER> [--output <OUTPUT_FILE>]
```

**Arguments:**

| Argument   | Description                                                                                          |
|------------|------------------------------------------------------------------------------------------------------|
| `--folder` | Path to the folder containing the translated JSONL chunk files                                       |
| `--output` | *(Optional)* Name of the output file. If omitted, it is derived from the common prefix of the input files (e.g., `Factbench_vi.jsonl`) |

**Example** — merge all files in `tl-res/`:

```sh
python merge_jsonl.py --folder tl-res
```

This produces `Factbench_vi.jsonl`.

Or specify a custom output filename:

```sh
python merge_jsonl.py --folder tl-res --output my_output.jsonl
```

> **Note:** The script checks that the chunk files form a continuous range (e.g., `1-10`, `11-30`, `31-50`, …) and warns if any file has an unexpected line count.