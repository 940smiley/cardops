from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cardops_api.audit import add_audit_log
from cardops_api.models import CardInstance, FieldProvenance, utc_now
from cardops_api.schemas import CardCreate, CardUpdate

PROVENANCE_FIELDS = {
    "sport",
    "player",
    "team",
    "manufacturer",
    "brand",
    "set_name",
    "set_year",
    "card_number",
    "subset",
    "variation",
    "parallel",
    "rookie",
    "autograph",
    "relic",
    "serial_number_current",
    "serial_number_total",
    "raw_or_graded",
    "grading_company",
    "grade",
    "quantity",
    "condition_notes",
    "estimated_value",
    "storage_location",
    "tags",
}


def generate_sku(session: Session) -> str:
    total = session.scalar(select(func.count()).select_from(CardInstance)) or 0
    candidate_number = total + 1
    while True:
        sku = f"COA-{candidate_number:06d}"
        if session.scalar(select(CardInstance).where(CardInstance.internal_sku == sku)) is None:
            return sku
        candidate_number += 1


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(float(value))
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def _add_provenance(
    session: Session,
    card: CardInstance,
    field_name: str,
    value: Any,
    *,
    source_type: str,
    source_identifier: str,
    confidence: float | None = None,
    user_override: bool = False,
) -> None:
    session.add(
        FieldProvenance(
            entity_type="card_instance",
            entity_id=card.id,
            field_name=field_name,
            value=_stringify(value),
            normalized_value=_stringify(value).lower() if isinstance(value, str) else _stringify(value),
            source_type=source_type,
            source_identifier=source_identifier,
            confidence=confidence,
            model_or_engine="manual",
            schema_version="1",
            user_override=user_override,
        )
    )


def create_card(session: Session, payload: CardCreate, *, source_identifier: str = "manual") -> CardInstance:
    data = payload.model_dump()
    card = CardInstance(internal_sku=generate_sku(session), **data)
    session.add(card)
    session.flush()
    for field_name in PROVENANCE_FIELDS:
        _add_provenance(
            session,
            card,
            field_name,
            getattr(card, field_name),
            source_type="MANUAL_VALUE",
            source_identifier=source_identifier,
            confidence=card.confidence,
            user_override=True,
        )
    add_audit_log(session, "card.created", entity_type="card_instance", entity_id=card.id)
    session.commit()
    session.refresh(card)
    return card


def update_card(session: Session, card: CardInstance, payload: CardUpdate) -> CardInstance:
    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(card, field_name, value)
        if field_name in PROVENANCE_FIELDS:
            _add_provenance(
                session,
                card,
                field_name,
                value,
                source_type="MANUAL_VALUE",
                source_identifier="manual-update",
                confidence=updates.get("confidence", card.confidence),
                user_override=True,
            )
    card.updated_at = utc_now()
    session.add(card)
    add_audit_log(
        session,
        "card.updated",
        entity_type="card_instance",
        entity_id=card.id,
        details={"fields": sorted(updates.keys())},
    )
    session.commit()
    session.refresh(card)
    return card
