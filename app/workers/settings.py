from typing import Any

from arq.connections import RedisSettings

from app.config import get_settings
from app.pipeline import PipelineRunner
from app.schemas import JobEnqueuePayload
from app.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def process_document(ctx: dict[str, Any], payload: dict[str, Any]) -> dict[str, str]:
    """ARQ worker task: pick a job from Redis and run the full pipeline."""
    job_payload = JobEnqueuePayload.model_validate(payload)
    job_id = job_payload.job_id

    logger.info("worker_job_started", job_id=str(job_id))
    runner = PipelineRunner()
    output = await runner.run(job_id)
    logger.info("worker_job_finished", job_id=str(job_id), status=output.status)
    return {"job_id": str(job_id), "status": output.status.value}


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    logger.info("worker_started", queue=WorkerSettings.queue_name)


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker_stopped")


class WorkerSettings:
    """ARQ worker configuration — Redis-backed job consumer (BullMQ-equivalent pattern)."""

    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    functions = [process_document]
    on_startup = startup
    on_shutdown = shutdown
    max_tries = get_settings().job_max_retries
    job_timeout = get_settings().job_timeout_seconds
    queue_name = get_settings().queue_name
