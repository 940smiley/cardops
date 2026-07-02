from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from cardops_api.audit import add_audit_log
from cardops_api.card_analysis import identify_image
from cardops_api.image_service import scan_directory
from cardops_api.models import ImageAsset, Job, utc_now

logger = structlog.get_logger(__name__)


def enqueue_job(
    session: Session,
    job_type: str,
    payload: dict[str, Any],
    *,
    max_attempts: int = 3,
) -> Job:
    job = Job(type=job_type, payload=payload, max_attempts=max_attempts)
    session.add(job)
    session.flush()
    add_audit_log(session, "job.enqueued", entity_type="job", entity_id=job.id, details=payload)
    session.commit()
    session.refresh(job)
    return job


def claim_next_job(session: Session) -> Job | None:
    job = session.scalar(
        select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(1)
    )
    if job is None:
        return None
    job.status = "running"
    job.started_at = utc_now()
    job.updated_at = utc_now()
    job.attempts += 1
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def run_job(session: Session, job: Job) -> Job:
    try:
        if job.cancellation_requested:
            job.status = "cancelled"
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            session.add(job)
            session.commit()
            return job

        if job.type == "directory_scan":
            result = scan_directory(
                session,
                job.payload["directory_id"],
                cancellation_check=lambda: bool(session.get(Job, job.id).cancellation_requested),
            )
        elif job.type == "image_identification":
            if "image_ids" in job.payload:
                result = {"images": []}
                for image_id in job.payload.get("image_ids") or []:
                    image = session.get(ImageAsset, image_id)
                    if image is not None:
                        result["images"].append(identify_image(image))
            else:
                image = session.get(ImageAsset, job.payload["image_id"])
                if image is None:
                    raise ValueError("Image not found.")
                result = identify_image(image)
        else:
            raise ValueError(f"Unsupported job type: {job.type}")

        job.status = "cancelled" if job.cancellation_requested else "succeeded"
        job.result = result
        job.error = None
        job.completed_at = utc_now()
        job.updated_at = utc_now()
        session.add(job)
        add_audit_log(session, "job.completed", entity_type="job", entity_id=job.id, details=result)
        session.commit()
        session.refresh(job)
        return job
    except Exception as exc:
        logger.exception("job_failed", job_id=job.id, job_type=job.type, error=str(exc))
        job.error = str(exc)
        job.updated_at = utc_now()
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.completed_at = utc_now()
        else:
            job.status = "queued"
        session.add(job)
        add_audit_log(
            session,
            "job.failed",
            entity_type="job",
            entity_id=job.id,
            details={"error": str(exc), "attempts": job.attempts},
        )
        session.commit()
        session.refresh(job)
        return job


def run_job_inline(session: Session, job: Job) -> Job:
    if job.status == "queued":
        job.status = "running"
        job.started_at = utc_now()
        job.updated_at = utc_now()
        job.attempts += 1
        session.add(job)
        session.commit()
        session.refresh(job)
    return run_job(session, job)


def request_cancel(session: Session, job: Job) -> Job:
    job.cancellation_requested = True
    if job.status == "queued":
        job.status = "cancelled"
        job.completed_at = utc_now()
    job.updated_at = utc_now()
    session.add(job)
    add_audit_log(session, "job.cancel_requested", entity_type="job", entity_id=job.id)
    session.commit()
    session.refresh(job)
    return job


def retry_job(session: Session, job: Job) -> Job:
    if job.status not in {"failed", "cancelled"}:
        return job
    job.status = "queued"
    job.error = None
    job.cancellation_requested = False
    job.completed_at = None
    job.updated_at = utc_now()
    session.add(job)
    add_audit_log(session, "job.retry_requested", entity_type="job", entity_id=job.id)
    session.commit()
    session.refresh(job)
    return job
