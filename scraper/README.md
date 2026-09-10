#  week-5 assignment-The Polite Scraper

## Target classification

- **Site:** Books to Scrape (books.toscrape.com)
- **Why:** An official public sandbox built specifically for practicing web
  scraping — confirmed by reading the site's own description.
- **Scope:** Only the first 3 catalogue pages (60 books total).
- **Data collected:** Book title, price, availability, rating, description,
  and page URL — all publicly displayed product info.
- **robots.txt result:** No robots.txt file found (404) — a missing file,
  not explicit permission, so I relied on the site's own stated purpose as
  a scraping sandbox instead.
- I will not reuse this code on another site without checking its rules and
  terms first.

## Run it

\`\`\`bash
cd scraper
pip install -r requirements.txt
python src/main.py
\`\`\`

Produces `output/books.json` (60 validated records) and `output/errors.json`.

## Politeness rules followed

- Identifies itself with a custom `User-Agent` header
- 10-second timeout on every request
- 0.5-second delay between real (non-cached) requests
- Checks HTTP status code before parsing anything
- Caches every fetched page locally so development never re-hits the site

## Record schema

Each record in `books.json`:

| Field | Type | Notes |
|---|---|---|
| title | string | |
| product_url | URL | canonical identity |
| price_gbp | number | parsed from price_text |
| price_text | string | original raw text, e.g. "£51.77" |
| availability_text | string | |
| rating_text | string or null | |
| description | string or null | some books have none |
| source_page | URL | which catalogue page it came from |
| fetched_at | ISO timestamp | when it was collected |

## Limitations

- No automated retry/failure-recovery testing was performed in this
  submission — the pipeline assumes all target pages return 200.
- No run report is generated at this time.

## Ethics note

I only scraped a site explicitly built for scraping practice, collected only
publicly visible data, and would not run this against a real production site
without first checking its terms of service and `robots.txt`.