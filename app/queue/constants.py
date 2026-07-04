"""Redis-backed job queue constants.

ARQ is used as the Python worker runtime. It provides BullMQ-equivalent semantics:
Redis-backed queues, worker pools, retries, and job timeouts.
"""

PROCESS_DOCUMENT_TASK = "process_document"
