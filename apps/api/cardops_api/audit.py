from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from cardops_api.logging_config import redact
from cardops_api.models import AuditLog


def add_audit_log(
    session: Session,
    action: str,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> AuditLog:
    record = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=redact(details or {}),
        sensitive_redacted=True,
        correlation_id=correlation_id,
    )
    session.add(record)
    return record
