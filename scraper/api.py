import os
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = FastAPI(title="Book Enrichment API")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel(os.environ["GEMINI_MODEL"])

PROMPT_PATH = Path(__file__).parent / "prompts" / "enrich-v1.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


# ---------- Schemas ----------

class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=5000)


class EnrichResponse(BaseModel):
    category: Literal["fiction", "nonfiction", "poetry", "children", "other"]
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)


# ---------- Endpoint ----------

@app.post("/enrich")
def enrich_book(request: EnrichRequest):
    if os.getenv("LLM_STUB") == "1":
        return EnrichResponse(
            category="fiction",
            summary="A stubbed summary for testing purposes.",
            confidence=0.5
        )

    user_message = f'Input: title="{request.title}", description="{request.description}"\nOutput:'

    response = model.generate_content(
        [SYSTEM_PROMPT, user_message],
        generation_config=genai.types.GenerationConfig(temperature=0.2)
    )

    # Stage 2: just return the raw text for now — parsing/validation comes in Stage 3
    return {"raw_response": response.text}