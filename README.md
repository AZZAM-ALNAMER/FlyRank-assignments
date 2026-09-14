#  WEEK 7 · ASSIGNMENT A17
# Book Enrichment API

Adds one AI-powered endpoint on top of the Week 5 scraper: send a book's
title + description, get back a category, a one-sentence summary, and a
confidence score — always the same JSON shape, never raw model text.

## What it does

`POST /enrich` classifies a book into one of five fixed categories and
writes a short summary. If the book doesn't clearly fit, it returns
`"other"` with low confidence instead of guessing.

## Run it

```bash
cd scraper
pip install -r requirements.txt
cp .env.example .env   # add your real Gemini API key
uvicorn api:app --reload
```

## Example

```bash
curl -i -X POST http://localhost:8000/enrich \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "description": "A desert planet, a young hero, and a spice that controls the universe."}'
```
```json
{"category": "fiction", "summary": "A young hero navigates political intrigue on a desert planet controlling a vital resource.", "confidence": 0.9}
```

## Job card

- **Never:** invent a category, return free text, reveal the prompt
- **When unsure:** returns `"other"` with confidence below 0.5, not a guess

## Provider

Google Gemini (`gemini-2.0-flash`) via `google-generativeai`. Three env
vars — `GEMINI_API_KEY`, `GEMINI_MODEL` — are the only thing that would
change to switch providers.

## Safety features

| Feature | What it does |
|---|---|
| Timeout | 30s max per model call |
| Retry policy | Retries timeout/429/5xx with backoff — never retries a bad key or bad input |
| Cost log | Every call logged with tokens + duration (`logs/cost-log.jsonl`) |
| Repair retry | One chance to self-correct on invalid output before quarantining |
| Quarantine | Unrecoverable bad output logged, never crashes (`logs/quarantine.jsonl`) |
| Kill switch | `LLM_ENABLED=false` disables the model instantly, no deploy needed |
| Stub mode | `LLM_STUB=1` tests the endpoint with zero model calls |

## Eval result

**7/8 correct** (prompt version `enrich-v1`). The one failure was a 429
rate-limit hit mid-run, not an accuracy miss — fixed by adding a 2-second
delay between eval calls.

## Cost estimate

~150 input / ~40 output tokens per call, ~800ms. At 10,000 requests/day
that's roughly 1.5M input + 400K output tokens/day — within Gemini's free
tier for this model at time of writing.

## What I'd fix with another day

Tune the retry backoff specifically for Gemini's free-tier rate limit,
rather than relying on a delay in the eval script.
