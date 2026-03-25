# TL-system-4-test-data

Bo script de:
- Dich JSONL tu tieng Anh sang tieng Viet (theo tung khoang dong)
- Gop cac file da dich thanh 1 file duy nhat

## Yeu cau

- Python 3.8+
- LibreTranslate server dang chay tai `http://127.0.0.1:5000`

## Cai dat

```bash
cd TL-system-4-test-data
pip install -r requirements.txt
```

## Chay LibreTranslate

Trong terminal khac:

```bash
libretranslate
```

## Su dung

### 1) Dich theo khoang dong

```bash
python translate_jsonl.py --start <START_LINE> --end <END_LINE>
```

Vi du:

```bash
python translate_jsonl.py --start 1 --end 10
```

Ket qua:
- `tl-res/Factbench_vi_1-10.jsonl`

### 2) Gop cac file da dich

```bash
python merge_jsonl.py --folder tl-res
```

Hoac dat ten output:

```bash
python merge_jsonl.py --folder tl-res --output Factbench_vi.jsonl
```

## Ghi chu

- `translate_jsonl.py` hien dang su dung endpoint LibreTranslate local co dinh tai `http://127.0.0.1:5000`.
- `merge_jsonl.py` se canh bao neu cac chunk khong lien tuc (vi du thieu `31-50`).
