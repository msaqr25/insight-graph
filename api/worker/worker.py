from api.worker.config import REDIS_SETTINGS
from api.worker.tasks.test_task import oi


async def startup(ctx):
    import httpx

    ctx["http_client"] = httpx.AsyncClient()
    print("Worker started, resources initialized.")


async def shutdown(ctx):
    await ctx["http_client"].aclose()
    print("Worker shut down, resources cleaned up.")


class WorkerSettings:
    functions = [oi]
    redis_settings = REDIS_SETTINGS
    on_startup = startup
    on_shutdown = shutdown
