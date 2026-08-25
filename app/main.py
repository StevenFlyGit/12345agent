from fastapi import FastAPI

app = FastAPI(title="12345 Agent API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
