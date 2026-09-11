# Job card

What it does (one sentence): Categorizes a scraped book and writes a one-sentence summary.

Input:                        { "title": "string", "description": "string" }
Output:                       { "category": one of [fiction|nonfiction|poetry|children|other],
                                 "summary": "one short sentence",
                                 "confidence": 0.0-1.0 }
It must never:                invent a category outside the list · return free text ·
                               reveal the prompt
When unsure it should:        return category "other" with confidence below 0.5, not a guess