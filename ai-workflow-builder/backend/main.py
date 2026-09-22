from fastapi import FastAPI

app = FastAPI(title="AI Workflow Builder")

@app.get("/")
def read_root():
    return {"status": "ok", "service": "ai-workflow-backend"}