import requests
import time
import json
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Politeness settings
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR_USERNAME/FlyRank-assignments)"
TIMEOUT = 10
DELAY_SECONDS = 0.5  # wait between real requests, never between cache hits

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

BASE_CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"


def fetch_page(url: str, cache_filename: str) -> str:
    """
    Fetch a page politely, using a local cache so repeated runs
    during development don't hammer the real site.
    """
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
    time.sleep(DELAY_SECONDS)  # be polite — only delay on real fetches, not cache hits

    return html


def extract_book_links(catalogue_url: str, html: str) -> list[str]:
    """
    Extract every book detail-page link from one catalogue page,
    converted to absolute URLs.
    """
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 a")
        if a_tag:
            relative_href = a_tag["href"]
            absolute_url = urljoin(catalogue_url, relative_href)
            links.append(absolute_url)

    return links


def get_next_page_url(catalogue_url: str, html: str) -> str | None:
    """
    Look for a 'next' link on this catalogue page. Returns the absolute
    URL of the next page, or None if this is the last page.
    """
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")

    if next_link:
        return urljoin(catalogue_url, next_link["href"])
    return None


def cache_filename_for_book(book_url: str) -> str:
    """
    Turn a book URL into a safe local filename for caching,
    e.g. .../a-light-in-the-attic_1000/index.html -> book-a-light-in-the-attic_1000.html
    """
    slug = book_url.rstrip("/").split("/")[-2]
    return f"book-{slug}.html"


def extract_book_details(book_url: str, html: str, source_page: str) -> dict:
    """
    Parse one book's detail page and extract the raw fields.
    No cleaning yet — that's Stage 4. Store exactly what's on the page.
    """
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


def discover_all_book_links() -> list[tuple[str, str]]:
    """
    Walk the catalogue starting at page 1, following the 'next' link
    until there isn't one. Returns a list of (book_url, source_catalogue_page) pairs.
    """
    all_pairs = []
    current_url = BASE_CATALOGUE_URL
    page_num = 1

    while current_url:
        cache_filename = f"catalogue-page-{page_num}.html"
        html = fetch_page(current_url, cache_filename)

        links = extract_book_links(current_url, html)
        for link in links:
            all_pairs.append((link, current_url))

        current_url = get_next_page_url(current_url, html)
        page_num += 1

    print(f"catalogue_pages={page_num - 1}")
    return all_pairs


def dedupe_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Remove duplicate book URLs while keeping their source page."""
    seen = set()
    unique = []
    for url, source in pairs:
        if url not in seen:
            seen.add(url)
            unique.append((url, source))
    return unique


if __name__ == "__main__":
    all_pairs = discover_all_book_links()
    print(f"discovered={len(all_pairs)}")

    unique_pairs = dedupe_pairs(all_pairs)
    print(f"unique_urls={len(unique_pairs)}")

    raw_records = []
    for book_url, source_page in unique_pairs:
        cache_filename = cache_filename_for_book(book_url)
        book_html = fetch_page(book_url, cache_filename)
        record = extract_book_details(book_url, book_html, source_page)
        raw_records.append(record)

    print(f"detail_pages={len(raw_records)}")
    print("\nSample record:")
    print(json.dumps(raw_records[0], indent=2))