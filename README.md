#Assignment-4 Auth · Login & protect (Supabase)

CRUD to-do API (FastAPI + Postgres) with Supabase Auth added: signup, login,
logout, and protected routes guarded by a reusable token-verification dependency.

## Setup

1. Create a free project at supabase.com, grab your Project URL + anon key
   from Settings → API
2. Turn off "Confirm email" under Authentication → Providers → Email
3. `cp .env.example .env` and fill in your values

## Run

\`\`\`bash
docker compose up --build
\`\`\`

Docs at `http://localhost:8000/docs`

## Endpoints

| Method | Path | Auth |
|---|---|---|
| POST | /auth/signup | No |
| POST | /auth/login | No |
| POST | /auth/logout | Yes |
| GET | /public/info | No |
| GET | /protected/profile | Yes |
| GET | /protected/dashboard | Yes |
| GET/POST/PUT/DELETE | /tasks... | No |

## Example

\`\`\`bash
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer <access_token>"
\`\`\`

![Swagger screenshot](swagger-auth-screenshot.png)