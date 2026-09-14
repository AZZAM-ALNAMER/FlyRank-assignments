import os
import json
import re
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
import google.generativeai as genai
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
    """
    Models sometimes wrap JSON in a code fence or add extra words.
    Strip that noise and return just the JSON object substring.
    """
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    brace_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)

    return raw_text


def call_model(user_message: str) -> str:
    response = model.generate_content(
        [SYSTEM_PROMPT, user_message],
        generation_config=genai.types.GenerationConfig(temperature=0.2)
    )
    return response.text


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


def parse_and_validate(raw_text: str) -> EnrichResponse | None:
    """Try to parse raw model text into a valid EnrichResponse. Returns None on failure."""
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

    user_message = f'Input: title="{request.title}", description="{request.description}"\nOutput:'

    # Attempt 1
    raw_text = call_model(user_message)
    result = parse_and_validate(raw_text)
    if result is not None:
        return result

    # Repair retry — give the model its own broken output + the error, ask it to fix it
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

    raw_text_retry = call_model(repair_message)
    result = parse_and_validate(raw_text_retry)
    if result is not None:
        return result

    # Give up cleanly
    log_quarantine(
        input_data=request.model_dump(),
        raw_output=raw_text_retry,
        error="Failed validation after one repair attempt"
    )
    raise HTTPException(
        status_code=422,
        detail="Model output could not be validated after a repair attempt."
    )