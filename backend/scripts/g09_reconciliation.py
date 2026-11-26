"""Offline preservation checks for G09 rehearsal manifests; never a migration.

Inputs are in-memory synthetic snapshots. No database, settings, filesystem,
network, storage adapter or application model is imported by this module.
Classification and target resolution must be supplied by a reviewed rehearsal.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from uuid import UUID


class ReconciliationError(ValueError):
    """Only a fixed code is exposed, never manifest values or private paths."""


@dataclass(frozen=True)
class AuditRecord:
    id: UUID
    event_type: str
    entity_type: str
    entity_id: UUID
    actor_id: UUID
    changed_fields: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True)
class ScopedAuditRecord:
    source_event_id: UUID
    scope: str
    organization_id: UUID | None
    record: AuditRecord


@dataclass(frozen=True)
class AttachmentRecord:
    id: UUID
    # All existing columns except id, including the four nullable resource FKs.
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class ScopedAttachmentRecord:
    organization_id: UUID
    record: AttachmentRecord


@dataclass(frozen=True)
class References:
    # A present key with value None represents an explicitly global resource.
    resources: Mapping[tuple[str, UUID], UUID | None]
    memberships: frozenset[tuple[UUID, UUID]]


@dataclass(frozen=True)
class ReconciliationSummary:
    audit_sources: int
    audit_projections: int
    audit_clones: int
    attachments: int


ATTACHMENT_FIELDS = frozenset(
    {
        "order_id",
        "trip_id",
        "delivery_id",
        "occurrence_id",
        "recorded_by",
        "event_id",
        "media_type",
        "size_bytes",
        "sha256",
        "fingerprint",
        "status",
        "recorded_at",
        "revoked_at",
        "revoked_by",
    }
)
RESOURCE_TYPES = {
    "order_id": "ORDER",
    "trip_id": "TRIP",
    "delivery_id": "DELIVERY",
    "occurrence_id": "OCCURRENCE",
}
Record = TypeVar("Record", AuditRecord, AttachmentRecord)


def _unique(records: Sequence[Record]) -> dict[UUID, Record]:
    indexed = {record.id: record for record in records}
    if len(indexed) != len(records):
        raise ReconciliationError("DUPLICATE_ID")
    return indexed


def _target(
    references: References,
    entity_type: str,
    entity_id: object,
    organization_id: UUID | None,
) -> None:
    if not isinstance(entity_id, UUID):
        raise ReconciliationError("INVALID_REFERENCE_ID")
    key = (entity_type, entity_id)
    if key not in references.resources:
        raise ReconciliationError("MISSING_REFERENCE")
    if references.resources[key] != organization_id:
        raise ReconciliationError("REFERENCE_SCOPE_MISMATCH")


def _member(references: References, organization_id: UUID, actor_id: object) -> None:
    if not isinstance(actor_id, UUID):
        raise ReconciliationError("INVALID_ACTOR_ID")
    if (organization_id, actor_id) not in references.memberships:
        raise ReconciliationError("MISSING_CONTEXTUAL_MEMBERSHIP")


def _user_partition(original: AuditRecord, item: ScopedAuditRecord) -> None:
    """Conservatively reject unresolved USER fields, without resolving targets."""
    if original.entity_type != "USER":
        return
    if original.event_type not in {"USER_CREATED", "USER_UPDATED"}:
        raise ReconciliationError("AUDIT_CLASSIFICATION_UNRESOLVED")
    targets = {
        **{
            field: ("USER_IDENTITY", "PLATFORM")
            for field in ("name", "email", "active", "password")
        },
        **{
            field: ("MEMBERSHIP", "ORGANIZATION")
            for field in ("role", "custom_profile_id", "driver_id")
        },
        "notification_preferences.SECURITY": ("NOTIFICATION_PREFERENCE", "PLATFORM"),
        "notification_preferences.TRIPS": ("NOTIFICATION_PREFERENCE", "ORGANIZATION"),
        "notification_preferences.OCCURRENCES": (
            "NOTIFICATION_PREFERENCE",
            "ORGANIZATION",
        ),
    }
    if any(field not in targets for field in original.changed_fields):
        raise ReconciliationError("AUDIT_CLASSIFICATION_UNRESOLVED")
    if any(
        targets.get(field) != (item.record.entity_type, item.scope)
        for field in item.record.changed_fields
    ):
        raise ReconciliationError("AUDIT_CLASSIFICATION_UNRESOLVED")
    if (
        item.record.entity_type == "USER_IDENTITY"
        and item.record.entity_id != original.entity_id
    ):
        raise ReconciliationError("AUDIT_CLASSIFICATION_UNRESOLVED")


def reconcile(
    audit_before: Sequence[AuditRecord],
    audit_after: Sequence[ScopedAuditRecord],
    attachments_before: Sequence[AttachmentRecord],
    attachments_after: Sequence[ScopedAttachmentRecord],
    references: References,
) -> ReconciliationSummary:
    """Reject loss, invented lineage, changed metadata and crossed references.

    Success proves only these manifest invariants, not correct classification,
    complete exports, blob contents, SQL constraints or runtime authorization.
    """
    originals = _unique(audit_before)
    projections = _unique([item.record for item in audit_after])
    fields: dict[UUID, Counter] = {identifier: Counter() for identifier in originals}
    retained = Counter()
    for item in audit_after:
        original = originals.get(item.source_event_id)
        if original is None:
            raise ReconciliationError("UNKNOWN_AUDIT_SOURCE")
        row = item.record
        if row.id in originals and row.id != original.id:
            raise ReconciliationError("AUDIT_ID_REASSIGNED")
        retained[original.id] += row.id == original.id
        if (row.actor_id, row.created_at) != (original.actor_id, original.created_at):
            raise ReconciliationError("AUDIT_METADATA_CHANGED")
        if item.scope == "PLATFORM":
            if item.organization_id is not None:
                raise ReconciliationError("INVALID_AUDIT_SCOPE")
        elif item.scope == "ORGANIZATION" and item.organization_id is not None:
            _member(references, item.organization_id, row.actor_id)
        else:
            raise ReconciliationError("INVALID_AUDIT_SCOPE")
        _user_partition(original, item)
        _target(references, row.entity_type, row.entity_id, item.organization_id)
        if not row.changed_fields or len(set(row.changed_fields)) != len(
            row.changed_fields
        ):
            raise ReconciliationError("INVALID_CHANGED_FIELDS")
        fields[original.id].update(row.changed_fields)
    for identifier, original in originals.items():
        if retained[identifier] != 1:
            raise ReconciliationError("AUDIT_SOURCE_ID_NOT_PRESERVED")
        if len(set(original.changed_fields)) != len(original.changed_fields):
            raise ReconciliationError("INVALID_SOURCE_FIELDS")
        if fields[identifier] != Counter(original.changed_fields):
            raise ReconciliationError("AUDIT_FIELDS_NOT_PRESERVED")

    attachments = _unique(attachments_before)
    results = _unique([item.record for item in attachments_after])
    if attachments.keys() != results.keys():
        raise ReconciliationError("ATTACHMENT_IDS_NOT_PRESERVED")
    for item in attachments_after:
        row = item.record
        original = attachments[row.id]
        if set(original.metadata) != ATTACHMENT_FIELDS:
            raise ReconciliationError("INCOMPLETE_ATTACHMENT_MANIFEST")
        if dict(row.metadata) != dict(original.metadata):
            raise ReconciliationError("ATTACHMENT_METADATA_CHANGED")
        resources = [
            (kind, row.metadata[column])
            for column, kind in RESOURCE_TYPES.items()
            if row.metadata[column] is not None
        ]
        if len(resources) != 1:
            raise ReconciliationError("ATTACHMENT_RESOURCE_COUNT")
        kind, identifier = resources[0]
        _target(references, kind, identifier, item.organization_id)
        _member(references, item.organization_id, row.metadata["recorded_by"])
        if row.metadata["revoked_by"] is not None:
            _member(references, item.organization_id, row.metadata["revoked_by"])
    return ReconciliationSummary(
        len(originals),
        len(projections),
        len(projections) - len(originals),
        len(attachments),
    )
