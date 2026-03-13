import pandas as pd

# Đọc file dữ liệu
df = pd.read_csv("data/merged_vnexpress.csv")

# Kiểm tra dữ liệu
print("Tổng số dòng:", len(df))

# Nhóm theo category và subcategory rồi lấy 20 dòng ngẫu nhiên
sampled_df = (
    df.groupby(["category", "subcategory"], group_keys=False)
      .apply(lambda x: x.sample(n=min(20, len(x)), random_state=42))
)

# Reset index
sampled_df = sampled_df.reset_index(drop=True)

# Lưu ra file mới
sampled_df.to_csv("test_data.csv", index=False, encoding="utf-8-sig")

print("Đã tạo file test_data.csv")