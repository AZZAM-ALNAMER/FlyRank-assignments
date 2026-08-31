# A3 Containerize the stack

A CRUD API for managing a to-do list, built with FastAPI, now running against
a real PostgreSQL database inside Docker — the third storage engine this
project has used (memory → SQLite → Postgres).

## Run it (one command)

\`\`\`bash
cp .env.example .env
docker compose up
\`\`\`

Visit `http://localhost:8000/docs` for Swagger UI.

## Environment variables

See `.env.example` — set `DATABASE_URL` to point at your Postgres instance.

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

## Example

\`\`\`bash
curl -i http://localhost:8000/tasks
\`\`\`

## Persistence proof

Created a task, ran \`docker compose down\` then \`docker compose up\` again —
the task was still there, because the named volume (\`taskdata\`) keeps
Postgres's files outside the container's own lifecycle.

## Data in the database

\`\`\`bash
docker exec -it <container-name> psql -U postgres -d tasks -c "SELECT * FROM tasks;"
\`\`\`

![Postgres data screenshot](postgres-screenshot.png)