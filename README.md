# Week-2 Assignment( Connecting to the database)

A CRUD API for managing a to-do list, built with FastAPI, now backed by a real
SQLite database instead of an in-memory list — so data survives a server restart.

## Why SQLite

- Zero setup — no server to install or configure, it's just a file (`tasks.db`)
- Perfect for small apps and learning — same SQL you'd use on Postgres later
- Data persists across restarts, unlike the Week 2 in-memory version

## Where the database lives

`tasks.db` is created automatically the first time the app runs. It's git-ignored,
so every fresh clone starts with a clean database, auto-seeded with 3 example tasks.

## Run it

\`\`\`bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
\`\`\`

Visit `http://localhost:8000/docs` for Swagger UI.

## Endpoints

| Method | Path        | Description        |
|--------|-------------|---------------------|
| GET    | /           | API info            |
| GET    | /health     | Health check         |
| GET    | /tasks      | List all tasks       |
| GET    | /tasks/{id} | Get a single task     |
| POST   | /tasks      | Create a new task      |
| PUT    | /tasks/{id} | Update a task           |
| DELETE | /tasks/{id} | Delete a task             |

## Proof of persistence

Created a task, restarted the server, ran `GET /tasks` — the task was still there.
(Previously, in the Week 2 in-memory version, it would have vanished.)

## Exploring the database by hand

Opened `tasks.db` in DB Browser for SQLite and ran:

\`\`\`sql
SELECT * FROM tasks WHERE done = 1;
\`\`\`

This returned only the tasks marked as completed — confirming the API and DB Browser
read the exact same file, with no syncing needed.

![DB Browser screenshot](db-browser-screenshot.png)