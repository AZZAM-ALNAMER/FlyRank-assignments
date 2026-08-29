from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3

app = FastAPI()

DB_NAME = "tasks.db"


# ---------- Stage 0: DB connection + table creation + seeding ----------

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, like a dict
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Seed only if empty
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]

    if count == 0:
        seed_tasks = [
            ("Learn FastAPI", 0),
            ("Build a CRUD API", 0),
            ("Connect it to a database", 0),
        ]
        cursor.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)", seed_tasks
        )

    conn.commit()
    conn.close()


init_db()  # runs once when the app starts


# ---------- Request body schemas ----------

class TaskCreate(BaseModel):
    title: str
    done: Optional[bool] = False

class TaskUpdate(BaseModel):
    title: str
    done: bool


# ---------- Root & health ----------

@app.get("/")
def read_root():
    return {
        "name": "Task API",
        "version": "2.0",
        "storage": "SQLite",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------- Stage 1: Read ----------

@app.get("/tasks")
def get_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(row)


# ---------- Stage 2: Create ----------

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task.title, int(task.done))
    )
    conn.commit()
    new_id = cursor.lastrowid

    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)


# ---------- Stage 3: Update & Delete ----------

@app.put("/tasks/{task_id}")
def update_task(task_id: int, updated: TaskUpdate):
    if not updated.title or not updated.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    conn = get_connection()
    existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    if existing is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (updated.title, int(updated.done), task_id)
    )
    conn.commit()

    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    conn = get_connection()
    existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    if existing is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return