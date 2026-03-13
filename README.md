# Fact-Checking-NeuralFact

# Fact-Checking-NeuralFact

## Giới thiệu

**Fact-Checking-NeuralFact** là dự án xây dựng pipeline thu thập dữ liệu tin tức và tạo bộ dữ liệu phục vụ bài toán **fact-checking**.
Dữ liệu được thu thập từ trang báo **VnExpress**, sau đó được xử lý và sử dụng **LLM (DeepSeek)** để tự động sinh các **claim** đúng và sai nhằm đánh giá hệ thống kiểm chứng thông tin.

Pipeline của dự án bao gồm các bước:

1. Thu thập dữ liệu tin tức từ VnExpress
2. Tổng hợp dữ liệu thành một dataset hoàn chỉnh
3. Tạo tập dữ liệu test
4. Sử dụng LLM để sinh claim phục vụ fact-checking

---

# Cấu trúc thư mục

```
Fact-Checking-NeuralFact
│
├── data
│   ├── merged_vnexpress.csv
│   ├── fact_check_claims.csv
|   └── test_data.csv
│
├── vnexpress_crawler.py
├── merge_csv.py
├── create_testfile.py
├── fact_check_data.py
│
└── README.md
```

---

# Mô tả dữ liệu

Sau khi thu thập và tổng hợp, dataset có khoảng **5896 bài báo**, mỗi dòng tương ứng một bài viết với các trường:

| Column      | Mô tả           |
| ----------- | --------------- |
| id          | ID của bài báo  |
| url         | Link bài viết   |
| title       | Tiêu đề bài báo |
| description | Mô tả ngắn      |
| date        | Thời gian đăng  |
| category    | Danh mục chính  |
| subcategory | Danh mục con    |

---

# Quy trình chạy dự án

## Bước 1: Crawl dữ liệu từ VnExpress

Chạy file:

```
python vn_express_crawler.py
```

Script này sẽ thu thập dữ liệu tin tức từ trang **VnExpress**.

⚠️ **Lưu ý**

* Quá trình crawl **mất rất nhiều thời gian**
* Vì vậy **không khuyến khích chạy lại nếu đã có dữ liệu**

---

## Bước 2: Tổng hợp dữ liệu

Sau khi crawl xong, chạy:

```
python merge_csv.py
```

Script này sẽ:

* Gộp các file CSV đã crawl
* Tạo dataset tổng hợp:

```
data/merged_vnexpress.csv
```

Dataset này chứa **5896 dòng dữ liệu tin tức**.

---

## Bước 3: Tạo file test

Chạy file:

```
python create_testfile.py
```

Script này sẽ:

* Lọc dữ liệu từ dataset chính
* Tạo tập **test dataset**

---

## Bước 4: Sinh claim bằng LLM (DeepSeek)

Sử dụng **DeepSeek API** để tự động tạo claim phục vụ bài toán fact-checking.

Từ mỗi tin tức:

* LLM sẽ sinh **1 claim** ứng với **1 hàng** trong file test.
* Claim có thể:

  * **True** (đúng với bài báo)
  * **False** (thay đổi một số thông tin như thời gian, địa điểm, nhân vật...)

Kết quả được lưu trong file:

```
data/fact_check_claims.csv
```

File này gồm các cột:

| Column | Mô tả                    |
| ------ | ------------------------ |
| id     | ID bài báo               |
| claim  | Claim được tạo           |
| label  | Nhãn `true` hoặc `false` |

Ví dụ:

| id | claim                                                                          | label |
| -- | ------------------------------------------------------------------------------ | ----- |
| 15 | Hà Nội vận hành thử quy trình bỏ phiếu trước ngày bầu cử Quốc hội.             | true  |
| 27 | TP HCM đã hoàn tất việc bỏ phiếu chính thức cho cuộc bầu cử Quốc hội năm 2023. | false |

---

# Mục đích dataset

Dataset được tạo nhằm phục vụ các nhiệm vụ:

* **Fact-checking**
* **Claim verification**
* **Evaluation LLM**
* **Training / testing fact-checking models**

---

# Công nghệ sử dụng

* Python
* BeautifulSoup
* Pandas
* DeepSeek API
* Web Crawling

---

# Lưu ý

* Việc crawl dữ liệu từ VnExpress có thể mất nhiều thời gian
* Nên sử dụng dataset đã được lưu sẵn trong thư mục `data`
* Việc tạo claim bằng LLM cần **API key của DeepSeek**

---

