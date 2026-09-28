import sqlite3
from datetime import date
from pathlib import Path
from html import escape

from playwright.sync_api import sync_playwright
from report_data import get_report_data, DB_PATH

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


def get_all_books() -> list[tuple]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT title, price, rating FROM books ORDER BY title"
    ).fetchall()
    conn.close()
    return rows


def build_html(data: dict, all_books: list[tuple]) -> str:
    today = date.today().isoformat()

    top_5_rows = "".join(
        f"<tr><td>{escape(b['title'])}</td><td>£{b['price']:.2f}</td></tr>"
        for b in data["top_5_expensive"]
    )

    all_rows = "".join(
        f"<tr><td>{escape(title)}</td><td>£{price:.2f}</td><td>{rating}</td></tr>"
        for title, price, rating in all_books
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #222; margin: 0; }}
  h1 {{ margin-bottom: 4px; }}
  .date {{ color: #666; margin-bottom: 24px; }}
  .totals {{ display: flex; gap: 24px; margin-bottom: 24px; }}
  .card {{ border: 1px solid #ccc; border-radius: 6px; padding: 12px 20px; }}
  .card .value {{ font-size: 24px; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 32px; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 12px; }}
  th {{ background: #f0f0f0; }}

  /* Print CSS: the fix for the page-break trap */
  thead {{ display: table-header-group; }}   /* repeat header on every page */
  tr {{ break-inside: avoid; }}              /* never slice a row in half */
</style>
</head>
<body>
  <h1>Bookstore Report</h1>
  <div class="date">Generated {today}</div>

  <div class="totals">
    <div class="card"><div>Total books</div><div class="value">{data['total_books']}</div></div>
    <div class="card"><div>Average price</div><div class="value">£{data['average_price']:.2f}</div></div>
  </div>

  <h2>Top 5 most expensive</h2>
  <table>
    <thead><tr><th>Title</th><th>Price</th></tr></thead>
    <tbody>{top_5_rows}</tbody>
  </table>

  <h2>All books</h2>
  <table>
    <thead><tr><th>Title</th><th>Price</th><th>Rating</th></tr></thead>
    <tbody>{all_rows}</tbody>
  </table>
</body>
</html>"""


def render_pdf(html: str, output_path: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=str(output_path), format="A4", print_background=True)
        browser.close()


if __name__ == "__main__":
    data = get_report_data()
    books = get_all_books()
    html = build_html(data, books)
    out = REPORTS_DIR / "test.pdf"
    render_pdf(html, out)
    print(f"Wrote {out}")