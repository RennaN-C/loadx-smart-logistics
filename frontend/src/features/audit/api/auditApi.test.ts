import { describe, expect, it } from "vitest";

import { mapAuditEntryFromDto } from "./auditApi";

describe("mapAuditEntryFromDto", () => {
  it("converte o contrato de auditoria para camelCase sem inventar dados", () => {
    expect(
      mapAuditEntryFromDto({
        id: "a1",
        event_type: "STATUS_CHANGED",
        entity_type: "ORDER",
        entity_id: "o1",
        actor_id: "u1",
        actor_name: "Ana",
        old_status: "DRAFT",
        new_status: "READY",
        changed_fields: [],
        created_at: "2026-10-06T18:00:00Z",
      }),
    ).toEqual({
      id: "a1",
      eventType: "STATUS_CHANGED",
      entityType: "ORDER",
      entityId: "o1",
      actorId: "u1",
      actorName: "Ana",
      oldStatus: "DRAFT",
      newStatus: "READY",
      changedFields: [],
      createdAt: "2026-10-06T18:00:00Z",
    });
  });

  it("preserva evento de sistema sem ator", () => {
    const result = mapAuditEntryFromDto({
      id: "a2",
      event_type: "STATUS_CHANGED",
      entity_type: "TRIP",
      entity_id: "t1",
      actor_id: null,
      actor_name: null,
      old_status: null,
      new_status: "SCHEDULED",
      changed_fields: [],
      created_at: "2026-10-06T18:00:00Z",
    });

    expect(result.actorId).toBeNull();
    expect(result.actorName).toBeNull();
  });
});
