from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()

# ---------- Database (tasks) config — from Assignment 3 ----------

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    return psycopg.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]

    if count == 0:
        seed_tasks = [
            ("Learn FastAPI", False),
            ("Build a CRUD API", False),
            ("Connect it to a database", False),
        ]
        cursor.executemany(
            "INSERT INTO tasks (title, done) VALUES (%s, %s)", seed_tasks
        )

    conn.commit()
    cursor.close()
    conn.close()


init_db()


# ---------- Supabase (auth) config — new this assignment ----------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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
        "version": "4.0",
        "storage": "PostgreSQL (Docker)",
        "auth": "Supabase",
        "endpoints": ["/tasks", "/auth/signup", "/auth/login"]
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------- Tasks: Read ----------

@app.get("/tasks")
def get_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"id": r[0], "title": r[1], "done": r[2]} for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": row[0], "title": row[1], "done": row[2]}


# ---------- Tasks: Create ----------

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
        (task.title, task.done)
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": row[0], "title": row[1], "done": row[2]}


# ---------- Tasks: Update & Delete ----------

@app.put("/tasks/{task_id}")
def update_task(task_id: int, updated: TaskUpdate):
    if not updated.title or not updated.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    cursor.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
        (updated.title, updated.done, task_id)
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return {"id": row[0], "title": row[1], "done": row[2]}


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return