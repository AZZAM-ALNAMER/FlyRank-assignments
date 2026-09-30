import sqlite3
import json

DB_PATH = "report.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_report_data() -> dict:
    conn = get_connection()

    # 1. Total number of books
    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]

    # 2. Average price
    avg_price = conn.execute("SELECT AVG(price) FROM books").fetchone()[0]

    # 3. Top 5 most expensive books
    top_5_rows = conn.execute(
        "SELECT title, price FROM books ORDER BY price DESC LIMIT 5"
    ).fetchall()
    top_5_expensive = [{"title": title, "price": price} for title, price in top_5_rows]

    # 4. Number of books per star rating
    rating_rows = conn.execute(
        "SELECT rating, COUNT(*) FROM books GROUP BY rating ORDER BY rating"
    ).fetchall()
    books_per_rating = {str(rating): count for rating, count in rating_rows}

    conn.close()

    return {
        "total_books": total_books,
        "average_price": round(avg_price, 2),
        "top_5_expensive": top_5_expensive,
        "books_per_rating": books_per_rating
    }


def create_reports_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

if __name__ == "__main__":
    data = get_report_data()
    print(json.dumps(data, indent=2))