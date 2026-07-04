from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings
from app.schemas import JobEnqueuePayload
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


async def get_redis_pool() -> ArqRedis:
    settings = get_settings()
    return await create_pool(
        _redis_settings(),
        default_queue_name=settings.queue_name,
    )


async def enqueue_document_job(job_id: UUID) -> str:
    """Push a document processing job onto the Redis queue."""
    settings = get_settings()
    pool = await get_redis_pool()
    payload = JobEnqueuePayload(job_id=job_id)

    # Job timeout is configured on WorkerSettings.job_timeout, not per enqueue.
    job = await pool.enqueue_job(
        "process_document",
        payload.model_dump(mode="json"),
        _queue_name=settings.queue_name,
    )
    await pool.close()

    if job is None:
        msg = f"Failed to enqueue job {job_id}"
        raise RuntimeError(msg)

    logger.info("job_enqueued", job_id=str(job_id), queue_job_id=job.job_id)
    return job.job_id
