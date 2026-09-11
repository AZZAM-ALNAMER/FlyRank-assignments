import os
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Book Enrichment API")


# ---------- Schemas ----------

class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=5000)


class EnrichResponse(BaseModel):
    category: Literal["fiction", "nonfiction", "poetry", "children", "other"]
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)


# ---------- Endpoint ----------

@app.post("/enrich", response_model=EnrichResponse)
def enrich_book(request: EnrichRequest):
    if os.getenv("LLM_STUB") == "1":
        return EnrichResponse(
            category="fiction",
            summary="A stubbed summary for testing purposes.",
            confidence=0.5
        )

    raise HTTPException(status_code=501, detail="LLM call not implemented yet (Stage 2)")