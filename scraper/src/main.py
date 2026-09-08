import requests
import time
import json
import re
import hashlib
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError, HttpUrl

# Politeness settings
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR_USERNAME/FlyRank-assignments)"
TIMEOUT = 10
DELAY_SECONDS = 0.5

CACHE_DIR = Path(__file__).parent.parent / "cache"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

BASE_CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3  # hard cap — this assignment only scopes the first 3 pages


# ---------- Schema (Stage 4) ----------

class Book(BaseModel):
    title: str
    product_url: HttpUrl
    price_gbp: float
    price_text: str
    availability_text: str
    rating_text: str | None
    description: str | None
    source_page: HttpUrl
    fetched_at: str


# ---------- Fetching ----------

def fetch_page(url: str, cache_filename: str) -> str:
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        print(f"CACHE HIT: {cache_filename}")
        return cache_path.read_text(encoding="utf-8")

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url} — status {response.status_code}")

    html = response.text
    cache_path.write_text(html, encoding="utf-8")

    print(f"FETCH: {cache_filename} ({len(html)} bytes)")
    time.sleep(DELAY_SECONDS)

    return html


# ---------- Discovery ----------

def extract_book_links(catalogue_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 a")
        if a_tag:
            links.append(urljoin(catalogue_url, a_tag["href"]))
    return links


def get_next_page_url(catalogue_url: str, html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    return urljoin(catalogue_url, next_link["href"]) if next_link else None


def discover_all_book_links() -> list[tuple[str, str]]:
    all_pairs = []
    current_url = BASE_CATALOGUE_URL
    page_num = 1

    # Hard cap on the while loop itself — cannot exceed MAX_CATALOGUE_PAGES
    while current_url and page_num <= MAX_CATALOGUE_PAGES:
        cache_filename = f"catalogue-page-{page_num}.html"
        html = fetch_page(current_url, cache_filename)

        for link in extract_book_links(current_url, html):
            all_pairs.append((link, current_url))

        current_url = get_next_page_url(current_url, html)
        page_num += 1

    print(f"catalogue_pages={page_num - 1}")
    return all_pairs


def dedupe_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen = set()
    unique = []
    for url, source in pairs:
        if url not in seen:
            seen.add(url)
            unique.append((url, source))
    return unique


# ---------- Extraction ----------

def cache_filename_for_book(book_url: str) -> str:
    """
    Turn a book URL into a safe, short local filename for caching.
    Uses a hash instead of the raw slug, since some book titles/URLs
    are too long for Windows filesystem limits.
    """
    url_hash = hashlib.md5(book_url.encode()).hexdigest()[:10]
    return f"book-{url_hash}.html"


def extract_book_details(book_url: str, html: str, source_page: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one("div.product_main h1").get_text(strip=True)
    price_text = soup.select_one("p.price_color").get_text(strip=True)
    availability_text = soup.select_one("p.availability").get_text(strip=True)

    rating_tag = soup.select_one("p.star-rating")
    rating_classes = rating_tag.get("class", [])
    rating_text = next((c for c in rating_classes if c != "star-rating"), None)

    description_tag = soup.select_one("#product_description ~ p")
    description = description_tag.get_text(strip=True) if description_tag else None

    return {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }


# ---------- Normalization (Stage 4) ----------

def normalize_record(raw: dict) -> dict:
    """Convert raw text fields into clean, typed values."""
    normalized = dict(raw)

    price_match = re.search(r"[\d.]+", raw["price_text"])
    normalized["price_gbp"] = float(price_match.group()) if price_match else None

    return normalized


# ---------- Validation + storage (Stage 4) ----------

def validate_and_store(raw_records: list[dict]):
    valid_records = []
    error_records = []
    seen_urls = set()

    for raw in raw_records:
        normalized = normalize_record(raw)

        if normalized["product_url"] in seen_urls:
            continue

        try:
            book = Book(**normalized)
            valid_records.append(json.loads(book.model_dump_json()))
            seen_urls.add(normalized["product_url"])
        except ValidationError as e:
            error_records.append({
                "record": raw,
                "reason": str(e)
            })

    books_path = OUTPUT_DIR / "books.json"
    errors_path = OUTPUT_DIR / "errors.json"

    books_path.write_text(json.dumps(valid_records, indent=2), encoding="utf-8")
    errors_path.write_text(json.dumps(error_records, indent=2), encoding="utf-8")

    print(f"valid_records={len(valid_records)}")
    print(f"error_records={len(error_records)}")

    return valid_records, error_records


# ---------- Main ----------

if __name__ == "__main__":
    all_pairs = discover_all_book_links()
    print(f"discovered={len(all_pairs)}")

    unique_pairs = dedupe_pairs(all_pairs)
    print(f"unique_urls={len(unique_pairs)}")

    # Safety cap — this assignment only scopes the first 3 catalogue pages (60 books)
    if len(unique_pairs) > 60:
        print(f"WARNING: found {len(unique_pairs)} unique URLs, expected 60 — trimming to first 60")
        unique_pairs = unique_pairs[:60]

    raw_records = []
    for book_url, source_page in unique_pairs:
        cache_filename = cache_filename_for_book(book_url)
        book_html = fetch_page(book_url, cache_filename)
        record = extract_book_details(book_url, book_html, source_page)
        raw_records.append(record)

    print(f"detail_pages={len(raw_records)}")

    validate_and_store(raw_records)