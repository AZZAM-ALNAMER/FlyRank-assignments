# Week-2 Assignment - Task API 

A small CRUD API for managing a to-do list, built with FastAPI.
Data is stored in memory (no database yet — that's next week's assignment).

## Run it

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for interactive Swagger UI.

## Endpoints

| Method | Path           | Description              |
|--------|----------------|---------------------------|
| GET    | /              | API info                  |
| GET    | /health        | Health check               |
| GET    | /tasks         | List all tasks             |
| GET    | /tasks/{id}    | Get a single task          |
| POST   | /tasks         | Create a new task          |
| PUT    | /tasks/{id}    | Update a task               |
| DELETE | /tasks/{id}    | Delete a task                |

## Example

```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'
```

## Swagger UI

![Swagger screenshot](swagger-screenshot.png)