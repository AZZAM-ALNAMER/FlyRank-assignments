import requests
import os
from pathlib import Path

# Politeness settings
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/AZZAM-ALNAMER/FlyRank-assignments)"
TIMEOUT = 10  # seconds

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


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
    return html


if __name__ == "__main__":
    url = "https://books.toscrape.com/catalogue/page-1.html"
    html = fetch_page(url, "catalogue-page-1.html")
    print(f"Response size: {len(html)} characters")