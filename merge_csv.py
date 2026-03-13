"""
Merge VnExpress CSV Files
=========================

Gộp các file CSV danh mục VnExpress thành 1 file duy nhất.

Input columns:
id, date, url, title, description, content, category, subcategory

Output:
merged_vnexpress.csv (đã xoá cột description)
"""

import pandas as pd
from pathlib import Path

# Thư mục chứa CSV
DATA_DIR = Path(__file__).parent / "data"

FILES = [
    "Thời_sự.csv",
    "Thế_giới.csv",
    "Thể_thao.csv",
    "Sức_khỏe.csv",
    "Kinh_doanh.csv",
    "Khoa_học_-_Công_nghệ.csv",
    "Góc_nhìn.csv",
    "Giáo_dục.csv",
    "Giải_trí.csv",
    "Du_lịch.csv",
]


def load_csv(file_path):
    """Đọc CSV và chuẩn hoá cột"""
    
    df = pd.read_csv(
        file_path,
        encoding="utf-8-sig",
        engine="python",
        quotechar='"',
        on_bad_lines="skip"
    )

    # chuẩn hoá tên cột (tránh lỗi khoảng trắng)
    df.columns = df.columns.str.strip().str.lower()

    return df


def main():

    print("=" * 50)
    print("MERGING VNEXPRESS CSV FILES")
    print("=" * 50)

    dfs = []

    for file in FILES:

        path = DATA_DIR / file

        if not path.exists():
            print(f"⚠ Không tìm thấy: {file}")
            continue

        df = load_csv(path)

        print(f"✔ {file}: {len(df)} records")

        dfs.append(df)

    if not dfs:
        print("❌ Không có file nào để gộp")
        return

    # Gộp dữ liệu
    merged = pd.concat(dfs, ignore_index=True, sort=False)

    print("\nTổng sau khi gộp:", len(merged))

    # Xoá cột content
    if "content" in merged.columns:
        merged = merged.drop(columns=["content"])
        print("✂ Đã xoá cột content")

    # Loại bỏ trùng lặp theo URL
    if "url" in merged.columns:

        before = len(merged)

        merged = merged.drop_duplicates(subset=["url"], keep="first")

        after = len(merged)

        print(f"🧹 Đã xoá {before - after} bản ghi trùng")

    # Reset id
    merged = merged.reset_index(drop=True)

    if "id" in merged.columns:
        merged["id"] = merged.index + 1

    # Sắp xếp lại cột
    expected_cols = [
        "id",
        "date",
        "url",
        "title",
        "description",
        "category",
        "subcategory",
    ]

    merged = merged[[c for c in expected_cols if c in merged.columns]]

    # Lưu file
    output_path = DATA_DIR / "merged_vnexpress.csv"

    merged.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("\n✅ Hoàn thành!")
    print("File lưu tại:", output_path)
    print("Tổng số record:", len(merged))


if __name__ == "__main__":
    main()