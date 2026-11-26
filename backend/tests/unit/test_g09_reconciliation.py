"""Synthetic G09 preservation rehearsal, entirely independent of a database."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from scripts.g09_reconciliation import (
    AttachmentRecord,
    AuditRecord,
    ReconciliationError,
    References,
    ScopedAttachmentRecord,
    ScopedAuditRecord,
    reconcile,
)

ORG_A, ORG_B, ACTOR, USER, MEMBER, ORDER, EVENT, CLONE, ATTACHMENT = (
    UUID(int=value) for value in range(1, 10)
)
AT = datetime(2026, 11, 25, tzinfo=UTC)


def rehearsal():
    original = AuditRecord(
        EVENT, "USER_UPDATED", "USER", USER, ACTOR, ("email", "role"), AT
    )
    identity = replace(original, entity_type="USER_IDENTITY", changed_fields=("email",))
    membership = replace(
        original,
        id=CLONE,
        event_type="MEMBERSHIP_UPDATED",
        entity_type="MEMBERSHIP",
        entity_id=MEMBER,
        changed_fields=("role",),
    )
    metadata = {
        "order_id": ORDER,
        "trip_id": None,
        "delivery_id": None,
        "occurrence_id": None,
        "recorded_by": ACTOR,
        "event_id": UUID(int=10),
        "media_type": "image/png",
        "size_bytes": 12,
        "sha256": "a" * 64,
        "fingerprint": "b" * 64,
        "status": "ACTIVE",
        "recorded_at": AT,
        "revoked_at": None,
        "revoked_by": None,
    }
    attachment = AttachmentRecord(ATTACHMENT, metadata)
    return {
        "audit_before": [original],
        "audit_after": [
            ScopedAuditRecord(EVENT, "PLATFORM", None, identity),
            ScopedAuditRecord(EVENT, "ORGANIZATION", ORG_A, membership),
        ],
        "attachments_before": [attachment],
        "attachments_after": [ScopedAttachmentRecord(ORG_A, deepcopy(attachment))],
        "references": References(
            {
                ("USER_IDENTITY", USER): None,
                ("MEMBERSHIP", MEMBER): ORG_A,
                ("ORDER", ORDER): ORG_A,
            },
            frozenset({(ORG_A, ACTOR)}),
        ),
    }


def test_preserves_mixed_audit_lineage_and_attachment_without_mutating_inputs():
    inputs = rehearsal()
    before = deepcopy(inputs)
    summary = reconcile(**inputs)
    assert summary.audit_sources == 1
    assert summary.audit_projections == 2
    assert summary.audit_clones == 1
    assert summary.attachments == 1
    assert reconcile(**inputs) == summary
    assert inputs == before


@pytest.mark.parametrize(
    "which", ["audit_before", "audit_after", "attachments_before", "attachments_after"]
)
def test_rejects_duplicate_ids(which):
    inputs = rehearsal()
    inputs[which].append(inputs[which][0])
    with pytest.raises(ReconciliationError, match="^DUPLICATE_ID$"):
        reconcile(**inputs)


@pytest.mark.parametrize("field", ["actor_id", "created_at"])
def test_rejects_changed_audit_actor_or_timestamp(field):
    inputs = rehearsal()
    item = inputs["audit_after"][0]
    value = UUID(int=50) if field == "actor_id" else AT.replace(day=24)
    inputs["audit_after"][0] = replace(
        item, record=replace(item.record, **{field: value})
    )
    with pytest.raises(ReconciliationError, match="^AUDIT_METADATA_CHANGED$"):
        reconcile(**inputs)


def test_rejects_deleted_source_id_even_when_all_fields_survive():
    inputs = rehearsal()
    item = inputs["audit_after"][0]
    inputs["audit_after"][0] = replace(
        item, record=replace(item.record, id=UUID(int=51))
    )
    with pytest.raises(ReconciliationError, match="^AUDIT_SOURCE_ID_NOT_PRESERVED$"):
        reconcile(**inputs)


@pytest.mark.parametrize(
    "fields", [("role", "invented"), ("email",), ("role", "email")]
)
def test_rejects_lost_invented_or_duplicated_fields_across_projections(fields):
    inputs = rehearsal()
    item = inputs["audit_after"][1]
    inputs["audit_after"][1] = replace(
        item, record=replace(item.record, changed_fields=fields)
    )
    with pytest.raises(ReconciliationError, match="^AUDIT_CLASSIFICATION_UNRESOLVED$"):
        reconcile(**inputs)


def test_audit_projection_loss_is_detected_even_when_original_id_is_present():
    inputs = rehearsal()
    inputs["audit_after"] = inputs["audit_after"][:1]
    with pytest.raises(ReconciliationError, match="^AUDIT_FIELDS_NOT_PRESERVED$"):
        reconcile(**inputs)


@pytest.mark.parametrize("field", ["unknown_field", "notification_preferences.UNKNOWN"])
def test_unknown_user_fields_require_quarantine_instead_of_guessing_scope(field):
    inputs = rehearsal()
    inputs["audit_before"][0] = replace(
        inputs["audit_before"][0], changed_fields=("email", field)
    )
    with pytest.raises(ReconciliationError, match="^AUDIT_CLASSIFICATION_UNRESOLVED$"):
        reconcile(**inputs)


def test_membership_field_cannot_be_classified_as_global_identity():
    inputs = rehearsal()
    original = inputs["audit_before"][0]
    inputs["audit_after"] = [
        ScopedAuditRecord(
            EVENT, "PLATFORM", None, replace(original, entity_type="USER_IDENTITY")
        )
    ]
    with pytest.raises(ReconciliationError, match="^AUDIT_CLASSIFICATION_UNRESOLVED$"):
        reconcile(**inputs)


def test_rejects_missing_or_crossed_resource_reference():
    inputs = rehearsal()
    references = inputs["references"]
    for target in (None, ORG_B):
        resources = dict(references.resources)
        if target is None:
            del resources[("ORDER", ORDER)]
            code = "MISSING_REFERENCE"
        else:
            resources[("ORDER", ORDER)] = target
            code = "REFERENCE_SCOPE_MISMATCH"
        inputs["references"] = replace(references, resources=resources)
        with pytest.raises(ReconciliationError, match=f"^{code}$"):
            reconcile(**inputs)


def test_actor_membership_in_another_tenant_does_not_authorize_audit():
    inputs = rehearsal()
    inputs["references"] = replace(
        inputs["references"], memberships=frozenset({(ORG_B, ACTOR)})
    )
    with pytest.raises(ReconciliationError, match="^MISSING_CONTEXTUAL_MEMBERSHIP$"):
        reconcile(**inputs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "c" * 64),
        ("event_id", UUID(int=52)),
        ("recorded_at", AT.replace(day=24)),
        ("status", "REVOKED"),
        ("order_id", UUID(int=53)),
    ],
)
def test_rejects_changed_attachment_metadata(field, value):
    inputs = rehearsal()
    inputs["attachments_after"][0].record.metadata[field] = value
    with pytest.raises(ReconciliationError, match="^ATTACHMENT_METADATA_CHANGED$"):
        reconcile(**inputs)


def test_rejects_attachment_loss_and_unresolved_extra_resource():
    inputs = rehearsal()
    inputs["attachments_after"] = []
    with pytest.raises(ReconciliationError, match="^ATTACHMENT_IDS_NOT_PRESERVED$"):
        reconcile(**inputs)
    inputs = rehearsal()
    for item in (
        inputs["attachments_before"][0],
        inputs["attachments_after"][0].record,
    ):
        item.metadata["trip_id"] = UUID(int=54)
    with pytest.raises(ReconciliationError, match="^ATTACHMENT_RESOURCE_COUNT$"):
        reconcile(**inputs)


def test_revoked_attachment_requires_revoker_membership_and_preserves_history():
    inputs = rehearsal()
    revoker = UUID(int=55)
    for item in (
        inputs["attachments_before"][0],
        inputs["attachments_after"][0].record,
    ):
        item.metadata.update(status="REVOKED", revoked_at=AT, revoked_by=revoker)
    with pytest.raises(ReconciliationError, match="^MISSING_CONTEXTUAL_MEMBERSHIP$"):
        reconcile(**inputs)
    references = inputs["references"]
    inputs["references"] = replace(
        references, memberships=references.memberships | {(ORG_A, revoker)}
    )
    assert reconcile(**inputs).attachments == 1


def test_rejects_incomplete_attachment_manifest():
    inputs = rehearsal()
    for item in (
        inputs["attachments_before"][0],
        inputs["attachments_after"][0].record,
    ):
        del item.metadata["fingerprint"]
    with pytest.raises(ReconciliationError, match="^INCOMPLETE_ATTACHMENT_MANIFEST$"):
        reconcile(**inputs)


def test_rejects_unknown_audit_source_and_invalid_scope_without_echoing_payload():
    for change, code in [
        ({"source_event_id": UUID(int=56)}, "UNKNOWN_AUDIT_SOURCE"),
        ({"scope": "invented-private-value"}, "INVALID_AUDIT_SCOPE"),
        ({"organization_id": ORG_A}, "INVALID_AUDIT_SCOPE"),
    ]:
        inputs = rehearsal()
        inputs["audit_after"][0] = replace(inputs["audit_after"][0], **change)
        with pytest.raises(ReconciliationError) as error:
            reconcile(**inputs)
        assert str(error.value) == code
