import sqlite3
import json
from pathlib import Path

DB_PATH = "report.db"
BOOKS_JSON_PATH = "books.json"


def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            rating INTEGER NOT NULL,
            url TEXT NOT NULL
        )
    """)


def clear_table(conn):
    conn.execute("DELETE FROM books")


RATING_WORD_TO_NUMBER = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5
}


def seed():
    conn = sqlite3.connect(DB_PATH)
    create_table(conn)
    clear_table(conn)  # run twice = still one clean copy

    books_data = json.loads(Path(BOOKS_JSON_PATH).read_text(encoding="utf-8"))

    rows = []
    for book in books_data:
        rating_word = book.get("rating_text")
        rating_number = RATING_WORD_TO_NUMBER.get(rating_word, 0)
        rows.append((
            book["title"],
            book["price_gbp"],
            rating_number,
            book["product_url"]
        ))

    conn.executemany(
        "INSERT INTO books (title, price, rating, url) VALUES (?, ?, ?, ?)",
        rows
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    print(f"Seeded {count} books.")

    conn.close()


if __name__ == "__main__":
    seed()