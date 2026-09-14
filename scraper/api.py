import os
import json
import re
import time
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from datetime import datetime, timezone

load_dotenv()

app = FastAPI(title="Book Enrichment API")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel(os.environ["GEMINI_MODEL"])

PROMPT_PATH = Path(__file__).parent / "prompts" / "enrich-v1.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
PROMPT_VERSION = "enrich-v1"

LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
QUARANTINE_PATH = LOGS_DIR / "quarantine.jsonl"
COST_LOG_PATH = LOGS_DIR / "cost-log.jsonl"

TIMEOUT_SECONDS = 30
MAX_RETRIES = 2  # our own explicit retry count, not relying on SDK defaults


# ---------- Schemas ----------

class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=5000)


class EnrichResponse(BaseModel):
    category: Literal["fiction", "nonfiction", "poetry", "children", "other"]
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)


# ---------- Helpers ----------

def extract_json_text(raw_text: str) -> str:
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    brace_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    return raw_text


def log_cost(input_tokens: int, output_tokens: int, duration_ms: float, needed_repair: bool):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": os.environ["GEMINI_MODEL"],
        "prompt_version": PROMPT_VERSION,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": round(duration_ms, 1),
        "needed_repair": needed_repair
    }
    with open(COST_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def log_quarantine(input_data: dict, raw_output: str, error: str):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": input_data,
        "raw_output": raw_output,
        "error": error
    }
    with open(QUARANTINE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def call_model(messages: list[str]) -> tuple[str, int, int, float]:
    """
    Calls the model with a timeout and retry policy.
    Retries on timeouts, 429 (rate limit), and 5xx server errors.
    Never retries on 400/401/403 — those won't fix themselves.
    Returns (text, input_tokens, output_tokens, duration_ms).
    """
    attempt = 0
    delay = 1

    while True:
        attempt += 1
        start = time.monotonic()
        try:
            response = model.generate_content(
                messages,
                generation_config=genai.types.GenerationConfig(temperature=0.2),
                request_options={"timeout": TIMEOUT_SECONDS}
            )
            duration_ms = (time.monotonic() - start) * 1000

            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count

            return response.text, input_tokens, output_tokens, duration_ms

        except google_exceptions.DeadlineExceeded:
            if attempt > MAX_RETRIES:
                raise HTTPException(status_code=504, detail="Model call timed out after retries.")
            time.sleep(delay)
            delay *= 2

        except google_exceptions.ResourceExhausted:
            # 429 — rate limited. Worth retrying with backoff.
            if attempt > MAX_RETRIES:
                raise HTTPException(status_code=429, detail="Rate limited by model provider.")
            time.sleep(delay)
            delay *= 2

        except google_exceptions.ServiceUnavailable:
            # 5xx — server-side issue. Worth retrying.
            if attempt > MAX_RETRIES:
                raise HTTPException(status_code=502, detail="Model provider unavailable.")
            time.sleep(delay)
            delay *= 2

        except (google_exceptions.InvalidArgument, google_exceptions.PermissionDenied,
                google_exceptions.Unauthenticated):
            # 400/401/403 equivalents — never retry, these won't fix themselves
            raise HTTPException(status_code=502, detail="Model provider rejected the request (bad key or bad input).")


def parse_and_validate(raw_text: str) -> EnrichResponse | None:
    json_text = extract_json_text(raw_text)
    try:
        data = json.loads(json_text)
        return EnrichResponse(**data)
    except (json.JSONDecodeError, ValidationError):
        return None


# ---------- Endpoint ----------

@app.post("/enrich", response_model=EnrichResponse)
def enrich_book(request: EnrichRequest):
    if os.getenv("LLM_STUB") == "1":
        return EnrichResponse(
            category="fiction",
            summary="A stubbed summary for testing purposes.",
            confidence=0.5
        )

    # Kill switch — instantly disable the model call, no deploy needed
    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        return EnrichResponse(
            category="other",
            summary="Enrichment temporarily unavailable.",
            confidence=0.0
        )

    user_message = f'Input: title="{request.title}", description="{request.description}"\nOutput:'

    # Attempt 1
    raw_text, in_tok, out_tok, duration = call_model([SYSTEM_PROMPT, user_message])
    result = parse_and_validate(raw_text)

    if result is not None:
        log_cost(in_tok, out_tok, duration, needed_repair=False)
        return result

    # Repair retry
    json_text = extract_json_text(raw_text)
    try:
        json.loads(json_text)
        error_detail = "Parsed as JSON but failed schema validation."
    except json.JSONDecodeError as e:
        error_detail = f"Could not parse as JSON: {e}"

    repair_message = (
        f"{user_message}\n\n"
        f"Your previous answer was rejected for this reason: {error_detail}\n"
        f"Your previous answer was: {raw_text}\n"
        f"Return only corrected JSON matching the schema."
    )

    raw_text_retry, in_tok2, out_tok2, duration2 = call_model([SYSTEM_PROMPT, repair_message])
    result = parse_and_validate(raw_text_retry)

    if result is not None:
        log_cost(in_tok + in_tok2, out_tok + out_tok2, duration + duration2, needed_repair=True)
        return result

    log_cost(in_tok + in_tok2, out_tok + out_tok2, duration + duration2, needed_repair=True)
    log_quarantine(
        input_data=request.model_dump(),
        raw_output=raw_text_retry,
        error="Failed validation after one repair attempt"
    )
    raise HTTPException(
        status_code=422,
        detail="Model output could not be validated after a repair attempt."
    )