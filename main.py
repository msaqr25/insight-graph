from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def check_health() -> dict[str, str]:
    return {"status": "ok"}
