import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse

def analyze_and_plot(compare_csv="compare_result.csv", merged_csv=r"../../data/merged_vnexpress.csv", output_img="analysis_chart.png"):
    if not os.path.exists(compare_csv):
        print(f"File {compare_csv} không tồn tại!")
        return
        
    if not os.path.exists(merged_csv):
        print(f"File {merged_csv} không tồn tại!")
        return

    # 1. Đọc file compare_result.csv
    try:
        df_compare = pd.read_csv(compare_csv, on_bad_lines='skip')
    except Exception as e:
        print(f"Lỗi đọc file {compare_csv}: {e}")
        return
    
    # Đảm bảo cột ID là kiểu số
    df_compare = df_compare.dropna(subset=['ID'])
    df_compare = df_compare[df_compare['ID'].apply(lambda x: str(x).replace('.0', '').isnumeric())]
    df_compare['ID'] = pd.to_numeric(df_compare['ID'])
    
    # 2. Đọc file merged_vnexpress.csv
    df_merged_src = pd.read_csv(merged_csv)
    
    # 3. Ghép nối để lấy category / subcategory
    df_merged = pd.merge(df_compare, df_merged_src, left_on='ID', right_on='id', how='inner')
    print(f"Đã ghép nối {len(df_merged)} câu từ {compare_csv} và {merged_csv}.")
    
    # Tạo cột 'Thể loại' từ category và subcategory
    df_merged['Thể loại'] = df_merged['category'] + ", " + df_merged['subcategory']
    
    # 4. Thống kê theo từng loại
    stats = df_merged.groupby(['Thể loại', 'Is_True']).size().unstack(fill_value=0)
    
    # Chuyển tên cột thành chuỗi để tránh bị pandas hiểu là mảng boolean
    stats.columns = [str(c) for c in stats.columns]
    
    # Đảm bảo có cả cột True và False kể cả khi không có dữ liệu
    if 'True' not in stats.columns:
        stats['True'] = 0
    if 'False' not in stats.columns:
        stats['False'] = 0
        
    stats = stats[['True', 'False']].copy()
    stats.columns = ['Đúng', 'Sai']
    stats['Tổng'] = stats['Đúng'] + stats['Sai']
    stats = stats.sort_values(by='Tổng', ascending=False)
    
    print("\nTHỐNG KÊ CHI TIẾT THEO TỪNG LOẠI:")
    print(stats)
    
    # In Confusion Matrix
    print("\n--- CONFUSION MATRIX ---")
    try:
        cm = pd.crosstab(df_merged['Expected'], df_merged['Answer'], 
                         rownames=['Thực tế (Expected)'], 
                         colnames=['Dự đoán (Answer)'], 
                         margins=True, margins_name='Tổng')
        print(cm)
    except Exception as e:
        print(f"Không thể tạo Confusion Matrix: {e}")

    # 6. Tính Accuracy
    try:
        total = len(df_merged)
        correct = df_merged['Is_True'].sum()  # True = 1, False = 0
        accuracy = correct / total if total > 0 else 0

        print("\n--- ACCURACY ---")
        print(f"Tổng số mẫu: {total}")
        print(f"Số dự đoán đúng: {correct}")
        print(f"Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")

    except Exception as e:
        print(f"Không thể tính Accuracy: {e}")
    
    # 5. Vẽ biểu đồ
    sns.set_theme(style="whitegrid")
    
    # Cấu hình font hỗ trợ tiếng Việt nếu có thể (tùy chọn)
    plt.rcParams['font.family'] = 'sans-serif'
    
    # Chuẩn bị dữ liệu vẽ bar chart (dạng dẹt để dễ dùng seaborn)
    plot_data = df_merged.groupby(['Thể loại', 'Is_True']).size().reset_index(name='Số lượng')
    plot_data['Is_True'] = plot_data['Is_True'].map({True: 'Đúng', False: 'Sai'})
    
    plt.figure(figsize=(14, 8))
    
    ax = sns.barplot(
        data=plot_data,
        x='Số lượng',
        y='Thể loại',
        hue='Is_True',
        palette={'Đúng': '#2ecc71', 'Sai': '#e74c3c'}
    )
    
    plt.title('Thống kê kết quả Dự đoán (Đúng/Sai) theo từng Thể loại\n(từ file merged_vnexpress.csv)', fontsize=14, pad=15)
    plt.xlabel('Số câu', fontsize=12)
    plt.ylabel('Thể loại (Category, Subcategory)', fontsize=12)
    plt.legend(title='Kết quả')
    
    # Hiển thị số liệu trực tiếp trên biểu đồ
    for p in ax.patches:
        width = p.get_width()
        if width > 0:
            ax.annotate(f'{int(width)}', 
                        (width, p.get_y() + p.get_height() / 2.),
                        ha='left', va='center', 
                        xytext=(5, 0), textcoords='offset points', 
                        fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_img, dpi=300)
    print(f"\nĐã xuất biểu đồ thống kê ra file ảnh: {output_img}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze claims results with merged_vnexpress and plot statistics.")
    parser.add_argument("--compare", type=str, default="compare_result.csv", help="Path to compare_result.csv")
    parser.add_argument("--merged", type=str, default=r"../../data/merged_vnexpress.csv", help="Path to merged_vnexpress.csv")
    parser.add_argument("--img", type=str, default="analysis_category_chart.png", help="Path to save the output chart image")
    
    args = parser.parse_args()
    analyze_and_plot(args.compare, args.merged, args.img)
