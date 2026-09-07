import requests
import time
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Politeness settings
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/AZZAM-ALNAMER/FlyRank-assignments)"
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


def discover_all_book_links() -> list[str]:
    """
    Walk the catalogue starting at page 1, following the 'next' link
    until there isn't one. Fetches each catalogue page exactly once,
    and extracts every book link along the way.
    """
    all_book_links = []
    current_url = BASE_CATALOGUE_URL
    page_num = 1

    while current_url:
        cache_filename = f"catalogue-page-{page_num}.html"
        html = fetch_page(current_url, cache_filename)

        links = extract_book_links(current_url, html)
        all_book_links.extend(links)

        current_url = get_next_page_url(current_url, html)
        page_num += 1

    print(f"catalogue_pages={page_num - 1}")
    return all_book_links


if __name__ == "__main__":
    all_book_links = discover_all_book_links()
    print(f"discovered={len(all_book_links)}")

    unique_urls = list(dict.fromkeys(all_book_links))  # dedupe, preserve order
    print(f"unique_urls={len(unique_urls)}")