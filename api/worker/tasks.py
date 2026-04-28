import asyncio


async def oi(ctx):
    print("Doing important stuff...")
    await asyncio.sleep(10)
    print("Done doing important stuff.")
    return {"status": "done"}
