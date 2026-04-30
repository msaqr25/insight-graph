import asyncio
from pathlib import Path

import httpx

PAPERS_DIR = Path("papers/")
API_URL = "http://localhost:8000/api"


async def ingest_all():
    async with httpx.AsyncClient() as client:
        for i, pdf in enumerate(PAPERS_DIR.glob("*.pdf")):
            with open(pdf, "rb") as f:
                resp = await client.post(
                    f"{API_URL}/upload", files={"file": (pdf.name, f, "application/pdf")}
                )
            doc_id = resp.json()["id"]
            print(f"{i + 1}. Uploaded {pdf.name} → document_id: {doc_id}")


asyncio.run(ingest_all())
