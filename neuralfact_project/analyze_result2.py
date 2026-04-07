import sys
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

print("Bắt đầu chạy script phân tích...")

# Fix encoding issue on Windows console to avoid UnicodeEncodeError
# if sys.stdout.encoding != 'utf-8':
#     sys.stdout.reconfigure(encoding='utf-8')

# Đường dẫn file compare_result.csv
# file_path = 'compare_result.csv'
# merged_csv_path = r'../../data/merged_vnexpress.csv'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

file_path = os.path.join(BASE_DIR, 'compare_result.csv')
merged_csv_path = os.path.join(BASE_DIR, '..', '..', 'data', 'merged_vnexpress.csv')

print("Current working dir:", os.getcwd())
print("Compare path:", file_path)
print("Merged path:", merged_csv_path)
try:
    print("Đang đọc file compare_result.csv...")
    # Đọc dữ liệu từ file
    df = pd.read_csv(file_path)
    
    # Lọc các dòng có Reason bắt đầu bằng chuỗi được yêu cầu
    target_reason = "Các mệnh đề kiểm chứng đều đúng theo bằng chứng xá"
    filtered_df = df[df['Reason'].str.startswith(target_reason, na=False)].copy()
    
    total_matches = len(filtered_df)
    print(f"Tổng số mệnh đề có Reason bắt đầu bằng '{target_reason}': {total_matches}")
    
    if total_matches > 0:
        # In ra confusion matrix thay vì chỉ số lượng đúng/sai
        print("\n=== CONFUSION MATRIX (Expected vs Answer) ===")
        cm = pd.crosstab(
            filtered_df['Expected'], 
            filtered_df['Answer'], 
            rownames=['Thực tế (Expected)'], 
            colnames=['Dự đoán (Answer)'], 
            margins=True
        )
        print(cm)
        
        # Thống kê tổng quan dựa trên đúng/sai
        correct_count = filtered_df[filtered_df['Is_True'] == True].shape[0]
        incorrect_count = filtered_df[filtered_df['Is_True'] == False].shape[0]
        print(f"\n- Tổng số dự đoán Đúng: {correct_count}")
        print(f"- Tổng số dự đoán Sai: {incorrect_count}")
        
        # --- PHÂN LOẠI THEO THỂ LOẠI VÀ VẼ BIỂU ĐỒ ---
        if os.path.exists(merged_csv_path):
            print(f"\nĐang đọc dữ liệu từ {merged_csv_path} để phân tích theo thể loại...")
            
            # Xử lý cột ID để merge
            filtered_df = filtered_df.dropna(subset=['ID'])
            filtered_df = filtered_df[filtered_df['ID'].apply(lambda x: str(x).replace('.0', '').isnumeric())]
            filtered_df['ID'] = pd.to_numeric(filtered_df['ID'])
            
            try:
                df_merged_src = pd.read_csv(merged_csv_path)
                # Ghép nối bằng ID
                df_merged = pd.merge(filtered_df, df_merged_src, left_on='ID', right_on='id', how='inner')
                
                if not df_merged.empty:
                    # Tạo cột Thể loại
                    df_merged['Thể loại'] = df_merged['category'] + ", " + df_merged['subcategory']
                    
                    # Tính thống kê
                    stats = df_merged.groupby(['Thể loại', 'Is_True']).size().unstack(fill_value=0)
                    stats.columns = [str(c) for c in stats.columns]
                    
                    if 'True' not in stats.columns:
                        stats['True'] = 0
                    if 'False' not in stats.columns:
                        stats['False'] = 0
                        
                    stats = stats[['True', 'False']].copy()
                    stats.columns = ['Đúng', 'Sai']
                    stats['Tổng'] = stats['Đúng'] + stats['Sai']
                    stats = stats.sort_values(by='Tổng', ascending=False)
                    
                    print("\n=== THỐNG KÊ CHI TIẾT THEO TỪNG THỂ LOẠI ===")
                    print(stats)
                    
                    # Vẽ biểu đồ
                    sns.set_theme(style="whitegrid")
                    plt.rcParams['font.family'] = 'sans-serif'
                    
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
                    
                    plt.title(f'Thống kê Đúng/Sai theo Thể loại\n(Đối với Reason: "{target_reason}...")', fontsize=14, pad=15)
                    plt.xlabel('Số lượng nhận định', fontsize=12)
                    plt.ylabel('Thể loại (Category, Subcategory)', fontsize=12)
                    plt.legend(title='Kết quả')
                    
                    # Thêm label số liệu cho từng cột
                    for p in ax.patches:
                        width = p.get_width()
                        if width > 0:
                            ax.annotate(f'{int(width)}', 
                                        (width, p.get_y() + p.get_height() / 2.),
                                        ha='left', va='center', 
                                        xytext=(5, 0), textcoords='offset points', 
                                        fontsize=10)
                    
                    plt.tight_layout()
                    output_img = 'analyze_result2_category_chart.png'
                    plt.savefig(output_img, dpi=300)
                    print(f"\nĐã xuất biểu đồ thống kê ra file ảnh: {output_img}")
                else:
                    print("\nKhông tìm thấy mẫu nào khớp ID giữa 2 file.")
            except Exception as e:
                print(f"Lỗi khi đọc và xử lý file gốc: {e}")
        else:
            print(f"\nKhông tìm thấy file nguồn {merged_csv_path} để gom nhóm theo thể loại.")
        
except FileNotFoundError:
    print(f"Không tìm thấy file {file_path}. Vui lòng kiểm tra lại đường dẫn.")
except Exception as e:
    print(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")
