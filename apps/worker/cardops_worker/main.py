from __future__ import annotations

import signal
import time

import structlog
from cardops_api.config import get_settings
from cardops_api.database import get_session_factory, init_db
from cardops_api.job_service import claim_next_job, run_job
from cardops_api.logging_config import configure_logging

logger = structlog.get_logger(__name__)
running = True


def _stop(_: int, __: object) -> None:
    global running
    running = False


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    logger.info("worker_started")
    session_factory = get_session_factory()
    while running:
        with session_factory() as session:
            job = claim_next_job(session)
            if job is None:
                time.sleep(1)
                continue
            logger.info("job_claimed", job_id=job.id, job_type=job.type)
            run_job(session, job)
    logger.info("worker_stopped")


if __name__ == "__main__":
    main()
