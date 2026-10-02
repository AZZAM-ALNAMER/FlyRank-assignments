# Assignment-8 PDF Report Generator

Generates a PDF report summarizing the bookstore dataset — total books, average
price, top 5 most expensive, and a per-rating breakdown — using SQLite,
raw SQL aggregation, and Playwright to render HTML into a downloadable PDF.

## Dataset

Bookstore data (60 books), reused from the scraper assignment's `books.json`
output — title, price, and star rating per book.

## Run it

```bash
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn playwright
playwright install chromium

python seed.py          # fills report.db from books.json (safe to re-run)
uvicorn main:app --reload
```

## Generate and download a report

```bash
curl -i -X POST http://localhost:8000/reports -H "Content-Type: application/json" -d "{}"
# -> 201 { "id": 1, "file": "/reports/1/file" }

curl -o my-report.pdf http://localhost:8000/reports/1/file
```

`my-report.pdf` opens as a real, multi-page PDF with a repeating table header
and no row cut across a page break.

## Aggregation SQL

```sql
SELECT COUNT(*) FROM books;

SELECT AVG(price) FROM books;

SELECT title, price FROM books ORDER BY price DESC LIMIT 5;

SELECT rating, COUNT(*) FROM books GROUP BY rating ORDER BY rating;
```

## Endpoints

| Method | Path | Returns |
|---|---|---|
| POST | /reports | 201 (new) or 200 (today's report already exists) + id + file link |
| GET | /reports/{id} | Report metadata. 404 if unknown. |
| GET | /reports/{id}/file | The actual PDF (only endpoint that moves bytes). |

## When would this move out of the request?

Right now `POST /reports` runs the whole pipeline synchronously, so the
caller waits a few seconds. That's fine for one user, one click. If reports
grew large (thousands of rows) or multiple users triggered generation at
once, I'd move the actual generation into a background job (e.g. via
Inngest) and have the client poll `GET /reports/{id}` until it's ready,
instead of holding the HTTP connection open.

## Idempotency (Stage 5)

`POST /reports` checks whether a report was already generated today before
creating a new one — two rapid POSTs return the same `id`, and only one new
file lands in `reports/`. This protects against something like a user
double-clicking "Generate," producing duplicate work and duplicate files.
A real-world parallel: a payment or email-send endpoint without this check
could charge or email a customer twice from one double-click.

## Screenshot (page 1 of a generated report)

![Report page 1](report-page-1-screenshot.png)
