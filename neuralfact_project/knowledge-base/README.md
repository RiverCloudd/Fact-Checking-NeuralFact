---
license: apache-2.0
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
dataset_info:
  features:
  - name: label
    dtype:
      class_label:
        names:
          '0': Thời sự
          '1': Thế giới
          '2': Kinh doanh
          '3': Khoa học
          '4': Bất động sản
          '5': Sức khỏe
          '6': Thể thao
          '7': Giải trí
          '8': Pháp luật
          '9': Giáo dục
          '10': Đời sống
  - name: title
    dtype: string
  - name: description
    dtype: string
  - name: text
    dtype: string
  splits:
  - name: train
    num_bytes: 735809126
    num_examples: 1348717
  download_size: 401116845
  dataset_size: 735809126
language:
- vi
pretty_name: Vietnamese News Classification Dataset
size_categories:
- 1M<n<10M
---

# Vietnamese News Classification Dataset (1.3M)

## Dataset Description

This dataset contains approximately **1.3 million** Vietnamese news articles collected from major online news portals. Structured similarly to the popular AG News dataset, it serves as a valuable resource for experimenting with multi-class text classification in Vietnamese.

The dataset covers **11 topics** (categories) ranging from current affairs, sports, technology, to entertainment.

- **Curated by:** Nam Syntax
- **Language:** Vietnamese
- **Total Rows:** ~1.3M
- **Task:** Multi-class Text Classification

## Dataset Structure

### Data Fields

Each instance in the dataset consists of the following fields:

- `label`: The category label id (Integer, 0-10).
- `title`: The title of the news article (String).
- `description`: A short summary/abstract of the article (String).
- `text`: The combination of title and description (and body content if available) used for training (String).

### Example

```json
{
"label": 0
"title": "Ba xe tông liên hoàn trên đường tránh Quảng Bình",
"description": "Xe khách bị rách hông bên phải sau cú tông vào xe tải chạy ngược chiều...",
"text": "Ba xe tông liên hoàn trên đường tránh Quảng Bình. Xe khách bị rách hông...",
}
```

| ID | Vietnamese Label | English Alias |
|:---:|:---|:---|
| 0 | Thời sự | current_affairs |
| 1 | Thế giới | world |
| 2 | Kinh doanh | business |
| 3 | Khoa học công nghệ | science_tech |
| 4 | Bất động sản | real_estate |
| 5 | Sức khỏe | health |
| 6 | Thể thao | sports |
| 7 | Giải trí | entertainment |
| 8 | Pháp luật | law |
| 9 | Giáo dục | education |
| 10 | Đời sống | lifestyle |