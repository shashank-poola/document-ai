def main() -> None:
    """Entry point for the document processing worker."""
    from arq import run_worker

    from app.workers.settings import WorkerSettings

    run_worker(WorkerSettings)
