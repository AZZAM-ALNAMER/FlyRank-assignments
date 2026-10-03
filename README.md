# Assignment-9 Background Job API

A small API where the slow work (an 8-second "report") happens in a
background job instead of inside the request — the endpoint answers
instantly, a status endpoint reports progress, and a cron job runs purely
on a schedule, with no request at all.

## Run it (two terminals)

**Terminal 1 — the API:**
```bash
cd background-job
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn inngest
uvicorn main:app --reload
```

**Terminal 2 — the Inngest Dev Server:**
```bash
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```

Dashboard: `http://localhost:8288`

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | /health | Health check |
| POST | /reports | Accepts a report request, returns 202 instantly |
| GET | /reports/{id} | Poll status: pending → done + result. 404 if unknown. |

## Background functions

| Function | Trigger | What it does |
|---|---|---|
| say-hello | event: test/hello | Sleeps 5s, returns a greeting (Stage 1 test function) |
| make-report | event: report/requested | Sleeps 8s, builds the report, updates its status |
| heartbeat | cron: `* * * * *` | Every minute, logs pending/done/failed counts |

## Proof: instant 202, then polling

```bash
curl -i -X POST http://localhost:8000/reports -H "Content-Type: application/json" -d "{\"topic\":\"cats\"}"
# -> 202, in well under a second
# {"id": "abc-123", "status": "pending"}

curl -i http://localhost:8000/reports/abc-123
# -> "status": "pending"

# wait ~10 seconds

curl -i http://localhost:8000/reports/abc-123
# -> "status": "done", with a result object
```

## Stage 3: why bad input never retries

A missing or empty topic is a client mistake, not a transient failure — it's
rejected immediately with 400, no event sent, no retry attempted. Retries
exist for temporary failures (a flaky network, a service hiccup) that might
succeed on a second try; a bad request will fail identically every time, so
retrying it would only waste time.

## Stage 4: cron expressions

- Every day at 08:00 → `0 8 * * *`
- Every Sunday at 22:00 → `0 22 * * 0`

## Dashboard screenshot

![Inngest dashboard](https://github.com/AZZAM-ALNAMER/FlyRank-assignments/blob/assignment-9/background-job/%7B1FF24428-F751-4E77-BDB9-96A9202CE303%7D.png?raw=true)
