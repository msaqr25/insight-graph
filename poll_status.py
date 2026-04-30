import asyncio

import httpx


async def check_all():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8000/api/documents")
        for i, doc in enumerate(resp.json()["documents"]):
            print(f"{i + 1:2d}. {doc['filename']:40s} → {doc['status']}")


asyncio.run(check_all())
