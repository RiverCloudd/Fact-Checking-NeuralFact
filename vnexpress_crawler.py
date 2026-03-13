"""
VnExpress News Crawler
======================

Crawl tin tức VnExpress từ năm 2020 đến nay, phân chia theo danh mục và tiểu danh mục.

Tác giả: Auto-generated
Phiên bản: 1.0
"""

import itertools
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import re
import logging
from datetime import datetime
from urllib.parse import urljoin


# ─────────────────────── Logging ───────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("crawler.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ─────────────────────── Cấu hình ───────────────────────
START_YEAR = 2026
END_DATE = datetime.now()

OUTPUT_DIR = "data"
DELAY = 1.5  # Giây chờ giữa các request (để không bị block)
MAX_RETRIES = 3


# Bộ đếm ID toàn cục (bắt đầu từ 1)
_article_id_gen = itertools.count(1)


def next_article_id() -> int:
    return next(_article_id_gen)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ─────────────────────────────────────────────────────────────────────────────
# Danh sách danh mục và tiểu danh mục theo cấu trúc VnExpress
# Mỗi mục: (tên_hiển_thị, slug_url)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────── Danh mục test (đủ bộ) ───────────
CATEGORIES = {
    "Thời sự": [
        ("Chính trị", "thoi-su/chinh-tri"),
        ("Kỷ nguyên mới", "thoi-su/huong-toi-ky-nguyen-moi"),
        ("Dân sinh", "thoi-su/dan-sinh"),
        ("Việc làm", "thoi-su/lao-dong-viec-lam"),
        # ("Pháp luật", "thoi-su/phap-luat"),
        ("Giao thông", "thoi-su/giao-thong"),
    ],

    "Thế giới": [
        ("Phân tích", "the-gioi/phan-tich"),
        ("Tư liệu", "the-gioi/tu-lieu"),
        ("Quân sự", "the-gioi/quan-su"),
        ("Cuộc sống đó đây", "the-gioi/cuoc-song-do-day"),
    ],

    "Kinh doanh": [
        ("Quốc tế", "kinh-doanh/quoc-te"),
        ("Doanh nghiệp", "kinh-doanh/doanh-nghiep"),
        ("Chứng khoán", "kinh-doanh/chung-khoan"),
        ("Vĩ mô", "kinh-doanh/vi-mo"),
        ("Hàng hóa", "kinh-doanh/hang-hoa"),
    ],

    "Khoa học - Công nghệ": [
        ("Chuyển đổi số", "khoa-hoc-cong-nghe/chuyen-doi-so"),
        ("AI", "khoa-hoc-cong-nghe/ai"),
        ("Thiết bị", "khoa-hoc-cong-nghe/thiet-bi"),
    ],

    "Góc nhìn": [
        ("Chính trị & chính sách", "goc-nhin/chinh-tri-chinh-sach"),
        ("Y tế & sức khỏe", "goc-nhin/y-te-suc-khoe"),
        ("Kinh doanh & quản trị", "goc-nhin/kinh-doanh-quan-tri"),
    ],

    "Sức khỏe": [
        ("Tin tức", "suc-khoe/tin-tuc"),
        ("Các bệnh", "suc-khoe/cac-benh"),
        ("Sống khỏe", "suc-khoe/song-khoe"),
    ],

    "Thể thao": [
        ("Bóng đá", "the-thao/bong-da"),
        ("Các môn khác", "the-thao/cac-mon-khac"),
    ],

    "Giải trí": [
        ("Giới sao", "giai-tri/gioi-sao"),
        ("Phim", "giai-tri/phim"),
    ],

    "Du lịch": [
        ("Điểm đến", "du-lich/diem-den"),
        ("Cẩm nang", "du-lich/cam-nang"),
    ],

    "Giáo dục": [
        ("Tin tức", "giao-duc/tin-tuc"),
        ("Tuyển sinh", "giao-duc/tuyen-sinh"),
    ],
}

BASE_URL = "https://vnexpress.net"


# ─────────────────────── Hàm tiện ích ───────────────────────
def get_html(url: str, retries: int = MAX_RETRIES) -> BeautifulSoup | None:
    """Tải HTML của một URL, tự thử lại khi lỗi."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")

        except requests.RequestException as e:
            logger.warning(f"Lần thử {attempt}/{retries} thất bại cho {url}: {e}")

            if attempt < retries:
                time.sleep(DELAY * attempt)

    return None


def parse_date(date_str: str) -> datetime | None:
    """
    Phân tích chuỗi ngày từ VnExpress.

    Xử lý các format phổ biến trên VnExpress, bao gồm:
    - Trang chi tiết: "Thứ năm, 5/3/2026, 14:26 (GMT+7)"
    - Trang listing: "10/3/2026, 08:30", datetime attribute ISO, v.v.
    """

    if not date_str:
        return None

    date_str = date_str.strip()

    # Loại bỏ phần tên ngày trong tuần ở đầu
    if date_str.startswith("Thứ") or date_str.startswith("Chủ nhật"):
        parts = date_str.split(",", 1)
        if len(parts) == 2:
            date_str = parts[1].strip()

    formats = [
        "%d/%m/%Y, %H:%M (GMT+7)",
        "%d/%m/%Y, %H:%M",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass

    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str)
    if match:
        try:
            return datetime(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1))
            )
        except ValueError:
            pass

    match = re.search(r"(\d{4})", date_str)
    if match:
        try:
            return datetime(int(match.group(1)), 1, 1)
        except ValueError:
            pass

    return None


def is_in_range(pub_date: datetime | None) -> bool | str:
    """
    Kiểm tra xem bài báo có nằm trong khoảng 2020 - hiện tại không.

    Trả về:
    True (trong tầm)
    False (quá mới - lỗi)
    'STOP' (quá cũ - dừng)
    """

    if pub_date is None:
        return True

    if pub_date.year < START_YEAR:
        return "STOP"

    if pub_date > END_DATE:
        return True

    return True

# ─────────────────────── Thu thập bài từ trang danh sách ───────────────────────
def get_article_links_from_page(soup: BeautifulSoup) -> list[dict]:
    """Lấy danh sách bài viết (url, title, description, pub_date) từ trang list."""

    articles = []
    seen_urls = set()

    # CSS selector chính cho các item bài viết
    selectors = [
        "article.item-news",
        "div.item-news",
        "article.item",
    ]

    items = []
    for sel in selectors:
        items = soup.select(sel)
        if items:
            break

    for item in items:

        # ── Tiêu đề + URL ──
        title_tag = item.select_one("h3.title-news a, h2.title-news a, h1.title-news a")

        if not title_tag:
            title_tag = item.select_one("a[title]")

        if not title_tag:
            continue

        url = title_tag.get("href", "")

        if not url.startswith("http"):
            url = urljoin(BASE_URL, url)

        # Lọc các URL không phải bài viết
        if "/video/" in url or not re.search(r"-\d+\.html$", url):
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        title = title_tag.get_text(strip=True)

        # ── Mô tả ──
        desc_tag = item.select_one("p.description, p.lead")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # ── Ngày xuất bản ──
        date_tag = item.select_one("span.time-count, span.date, time")

        pub_date_str = ""

        if date_tag:
            pub_date_str = (
                date_tag.get("datetime")
                or date_tag.get("title")
                or date_tag.get_text(strip=True)
            )

        pub_date = parse_date(pub_date_str)

        articles.append(
            {
                "url": url,
                "title": title,
                "description": description,
                "pub_date": pub_date,
                "pub_date_str": pub_date_str,
            }
        )

    return articles


# ─────────────────────── Thu thập nội dung bài viết ───────────────────────
def get_article_content(url: str, crawl_content: bool = True) -> dict:
    """
    Tải và trích xuất nội dung chi tiết của một bài báo.

    Luôn lấy date từ trang chi tiết (span.date).
    Nội dung bài chỉ lấy khi crawl_content=True.
    """

    soup = get_html(url)

    if not soup:
        return {"content": "", "date": ""}

    # ── Ngày xuất bản (lấy từ trang chi tiết) ──
    date_str = ""

    date_tag = soup.select_one("span.date")

    if date_tag:
        date_str = date_tag.get_text(strip=True)

    # ── Nội dung ──
    content = ""

    if crawl_content:

        content_div = soup.select_one(
            "article.fck_detail, div.fck_detail, div#article_content"
        )

        if content_div:

            # Loại bỏ các phần quảng cáo/script trong bài
            for tag in content_div(["script", "style", "figure", "figcaption", "ins"]):
                tag.decompose()

            content = content_div.get_text(separator="\n", strip=True)

    return {"content": content, "date": date_str}


# ─────────────────────── Crawl một tiểu danh mục ───────────────────────
def crawl_subcategory(
    category_name: str,
    sub_name: str,
    sub_slug: str,
    crawl_content: bool = True,
) -> list[dict]:
    """
    Crawl toàn bộ bài viết của một tiểu danh mục từ 2020 đến nay.

    Dừng khi gặp bài cũ hơn START_YEAR.
    """

    all_articles = []

    page = 1
    stop_crawling = False

    base_url = f"{BASE_URL}/{sub_slug}"

    logger.info(f" [{'Bắt đầu':^8}] {category_name} > {sub_name} ({base_url})")

    while not stop_crawling:

        # Xây dựng URL trang
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}-p{page}"

        soup = get_html(url)

        if not soup:
            logger.warning(f" Không tải được trang {page} - dừng danh mục này.")
            break

        # Kiểm tra nếu trang rỗng (không còn bài)
        articles = get_article_links_from_page(soup)

        if not articles:
            logger.info(f" Trang {page} không có bài viết - kết thúc.")
            break

        for art in articles:

            pub_date = art["pub_date"]

            in_range = is_in_range(pub_date)

            if in_range == "STOP":

                logger.info(
                    f" Gặp bài từ {pub_date.year if pub_date else 'N/A'} "
                    f"< {START_YEAR} → Dừng crawl danh mục này."
                )

                stop_crawling = True
                break

            # Chuẩn bị record
            time.sleep(DELAY)

            detail = get_article_content(
                art["url"],
                crawl_content=crawl_content,
            )

            # Ưu tiên date từ trang chi tiết
            date_from_detail = parse_date(detail["date"])

            if date_from_detail:

                date_val = date_from_detail.strftime("%Y-%m-%d %H:%M:%S")

                if date_from_detail.year < START_YEAR:

                    logger.info(
                        f" Gặp bài từ {date_from_detail.year} < {START_YEAR} "
                        f"→ Dừng crawl danh mục này."
                    )

                    stop_crawling = True
                    break

            else:

                date_val = (
                    art["pub_date"].strftime("%Y-%m-%d %H:%M:%S")
                    if art["pub_date"]
                    else art["pub_date_str"]
                )

            record = {
                "id": next_article_id(),
                "date": date_val,
                "url": art["url"],
                "title": art["title"],
                "description": art["description"],
                "content": detail["content"],
                "category": category_name,
                "subcategory": sub_name,
            }

            all_articles.append(record)

        logger.info(
            f" Trang {page} → +{len(articles)} bài "
            f"(tổng: {len(all_articles)})"
        )

        if not stop_crawling:
            page += 1
            time.sleep(DELAY)

    logger.info(f" [{'Hoàn tất':^8}] {sub_name}: {len(all_articles)} bài viết")

    return all_articles


# ─────────────────────── Lưu kết quả ───────────────────────
OUTPUT_COLUMNS = [
    "id",
    "date",
    "url",
    "title",
    "description",
    "content",
    "category",
    "subcategory",
]


def save_to_csv(data: list[dict], filepath: str):
    """Lưu danh sách bài viết ra file CSV theo thứ tự cột chuẩn."""

    if not data:
        logger.warning(f"Không có dữ liệu để lưu vào {filepath}")
        return

    df = pd.DataFrame(data, columns=OUTPUT_COLUMNS)

    df.to_csv(filepath, index=False, encoding="utf-8-sig")

    logger.info(f" Đã lưu {len(df)} bài → {filepath}")


# ─────────────────────── Main ───────────────────────
def main(
    crawl_content: bool = False,
    selected_categories: list[str] | None = None,
):
    """
    Hàm chính điều phối toàn bộ quá trình crawl.
    """

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("VnExpress Crawler khởi động")
    logger.info(f"Khoảng thời gian: {START_YEAR} → hiện tại")
    logger.info(f"Crawl nội dung đầy đủ: {crawl_content}")
    logger.info("=" * 60)

    categories_to_crawl = {
        k: v
        for k, v in CATEGORIES.items()
        if selected_categories is None or k in selected_categories
    }

    all_data = []

    for cat_name, cat_info in categories_to_crawl.items():

        logger.info(f"\n{'━'*50}")
        logger.info(f"DANH MỤC: {cat_name}")
        logger.info(f"{'━'*50}")

        cat_data = []

        for sub_name, sub_slug in cat_info:

            articles = crawl_subcategory(
                category_name=cat_name,
                sub_name=sub_name,
                sub_slug=sub_slug,
                crawl_content=crawl_content,
            )

            cat_data.extend(articles)
            all_data.extend(articles)

            if articles:

                safe_sub = re.sub(r'[\\/*?:"<>|]', "_", sub_name)

                sub_file = os.path.join(
                    OUTPUT_DIR,
                    f"{cat_name}_{safe_sub}.csv".replace(" ", "_"),
                )

                save_to_csv(articles, sub_file)

        if cat_data:

            safe_cat = re.sub(r'[\\/*?:"<>|]', "_", cat_name)

            cat_file = os.path.join(
                OUTPUT_DIR,
                f"{safe_cat}.csv".replace(" ", "_"),
            )

            save_to_csv(cat_data, cat_file)

    all_file = os.path.join(OUTPUT_DIR, "vnexpress_all.csv")

    save_to_csv(all_data, all_file)

    elapsed = datetime.now() - start_time

    logger.info(f"\n{'='*60}")
    logger.info(f"HOÀN TẤT! Tổng: {len(all_data)} bài viết")
    logger.info(f"Thời gian chạy: {elapsed}")
    logger.info(f"Dữ liệu lưu tại: {os.path.abspath(OUTPUT_DIR)}/")
    logger.info("=" * 60)

    return all_data


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="Crawl tin tức VnExpress từ 2020 đến nay"
    )

    parser.add_argument(
        "--content",
        action="store_true",
        help="Crawl nội dung đầy đủ bài viết",
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        help="Danh sách tên danh mục cần crawl",
        default=None,
    )

    args = parser.parse_args()

    main(
        crawl_content=args.content,
        selected_categories=args.categories,
    )