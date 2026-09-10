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
MAX_CATALOGUE_PAGES = 3

# Set this to True to test failure-handling with one fake URL (Stage 5 checkpoint)
INJECT_FAKE_URL_FOR_TESTING = False


# ---------- Schema ----------

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


# ---------- Fetching (Stage 5: retry + no crash) ----------

def fetch_page(url: str, cache_filename: str, allow_retry: bool = True) -> str | None:
    """
    Fetch a page politely. Returns the HTML string, or None if the
    fetch ultimately failed (caller is responsible for logging/skipping).
    Retries once on a timeout or 5xx server error. Never retries a
    404 (page doesn't exist) or 403 (site said no).
    """
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        print(f"CACHE HIT: {cache_filename}")
        return cache_path.read_text(encoding="utf-8")

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        if allow_retry:
            print(f"TIMEOUT: {url} — retrying once")
            time.sleep(1)
            return fetch_page(url, cache_filename, allow_retry=False)
        print(f"FAILED (timeout, gave up): {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"FAILED (connection error): {url} — {e}")
        return None

    if response.status_code == 200:
        html = response.text
        cache_path.write_text(html, encoding="utf-8")
        print(f"FETCH: {cache_filename} ({len(html)} bytes)")
        time.sleep(DELAY_SECONDS)
        return html

    if response.status_code in (404, 403):
        # Never retry — the page doesn't exist, or the site explicitly said no
        print(f"FAILED ({response.status_code}, no retry): {url}")
        return None

    if response.status_code >= 500 and allow_retry:
        print(f"SERVER ERROR ({response.status_code}): {url} — retrying once")
        time.sleep(1)
        return fetch_page(url, cache_filename, allow_retry=False)

    print(f"FAILED ({response.status_code}): {url}")
    return None


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

    while current_url and page_num <= MAX_CATALOGUE_PAGES:
        cache_filename = f"catalogue-page-{page_num}.html"
        html = fetch_page(current_url, cache_filename)

        if html is None:
            print(f"WARNING: catalogue page {page_num} failed — stopping discovery here")
            break

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


# ---------- Normalization ----------

def normalize_record(raw: dict) -> dict:
    normalized = dict(raw)
    price_match = re.search(r"[\d.]+", raw["price_text"])
    normalized["price_gbp"] = float(price_match.group()) if price_match else None
    return normalized


# ---------- Validation + storage ----------

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
    run_start = datetime.now(timezone.utc)

    all_pairs = discover_all_book_links()
    print(f"discovered={len(all_pairs)}")

    unique_pairs = dedupe_pairs(all_pairs)
    print(f"unique_urls={len(unique_pairs)}")

    if len(unique_pairs) > 60:
        print(f"WARNING: found {len(unique_pairs)} unique URLs, expected 60 — trimming to first 60")
        unique_pairs = unique_pairs[:60]

    # Stage 5 checkpoint: deliberately inject one fake book URL to prove
    # the run survives a broken page instead of crashing.
    if INJECT_FAKE_URL_FOR_TESTING:
        fake_url = "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html"
        unique_pairs.append((fake_url, BASE_CATALOGUE_URL))
        print("TESTING: injected one fake URL to verify failure handling")

    raw_records = []
    failed_pages = 0
    cache_hits = 0
    real_fetches = 0

    for book_url, source_page in unique_pairs:
        cache_filename = cache_filename_for_book(book_url)
        was_cached = (CACHE_DIR / cache_filename).exists()

        book_html = fetch_page(book_url, cache_filename)

        if book_html is None:
            print(f"SKIPPING broken page: {book_url}")
            failed_pages += 1
            continue

        if was_cached:
            cache_hits += 1
        else:
            real_fetches += 1

        record = extract_book_details(book_url, book_html, source_page)
        raw_records.append(record)

    print(f"detail_pages={len(raw_records)}")

    valid_records, error_records = validate_and_store(raw_records)

    run_end = datetime.now(timezone.utc)
    duration_seconds = (run_end - run_start).total_seconds()

    report = {
        "start_time": run_start.isoformat(),
        "end_time": run_end.isoformat(),
        "duration_seconds": round(duration_seconds, 2),
        "catalogue_pages_visited": MAX_CATALOGUE_PAGES,
        "book_pages_attempted": len(unique_pairs),
        "cache_hits": cache_hits,
        "real_fetches": real_fetches,
        "valid_records": len(valid_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages
    }

    report_path = OUTPUT_DIR / "run-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n--- RUN REPORT ---")
    print(json.dumps(report, indent=2))