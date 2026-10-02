import sqlite3
from datetime import datetime, date
from pathlib import Path
from fastapi import Response

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from report_data import get_report_data, create_reports_table, DB_PATH
from render import build_html, render_pdf, get_all_books

app = FastAPI(title="PDF Report Generator")

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    create_reports_table(conn)
    return conn


@app.get("/health")
def health():
    return {"status": "ok"}


class GenerateRequest(BaseModel):
    force: bool = False


@app.post("/reports")
def create_report(body: GenerateRequest, response: Response):
    conn = get_connection()

    if not body.force:
        today_prefix = date.today().isoformat()
        existing = conn.execute(
            "SELECT id, path, created_at FROM reports WHERE created_at LIKE ? ORDER BY id DESC LIMIT 1",
            (f"{today_prefix}%",)
        ).fetchone()

        if existing is not None:
            conn.close()
            response.status_code = 200
            return {"id": existing[0], "file": f"/reports/{existing[0]}/file"}

    data = get_report_data()
    books = get_all_books()
    html = build_html(data, books)

    output_path = REPORTS_DIR / f"report-{datetime.now().timestamp():.0f}.pdf"
    render_pdf(html, output_path)

    created_at = datetime.now().isoformat()
    cursor = conn.execute(
        "INSERT INTO reports (path, created_at) VALUES (?, ?)",
        (str(output_path), created_at)
    )
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()

    response.status_code = 201
    return {"id": report_id, "file": f"/reports/{report_id}/file"}

@app.get("/reports/{report_id}")
def get_report(report_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, path, created_at FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": row[0],
        "path": row[1],
        "created_at": row[2],
        "file": f"/reports/{row[0]}/file"
    }


@app.get("/reports/{report_id}/file")
def get_report_file(report_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT path FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")

    file_path = row[0]
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Report file missing on disk")

    return FileResponse(file_path, media_type="application/pdf", filename=f"report-{report_id}.pdf")