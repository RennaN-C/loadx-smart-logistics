export const AUDIT_ENTITY_TYPES = ["ORDER", "LOAD_PLAN", "TRIP", "DELIVERY", "USER", "LOAD_DISTRIBUTION", "LOAD_DISTRIBUTION_PART", "CUSTOMER", "PRODUCT", "TRUCK", "DRIVER"] as const;
export type AuditEntityType = (typeof AUDIT_ENTITY_TYPES)[number];

export const AUDIT_EVENT_TYPES = ["STATUS_CHANGED", "USER_CREATED", "USER_UPDATED", "RECORD_ARCHIVED", "RECORD_REACTIVATED"] as const;
export type AuditEventType = (typeof AUDIT_EVENT_TYPES)[number];

export interface AuditEntry {
  id: string;
  eventType: AuditEventType;
  entityType: AuditEntityType;
  entityId: string;
  actorId: string | null;
  actorName: string | null;
  oldStatus: string | null;
  newStatus: string | null;
  changedFields: string[];
  createdAt: string;
}

export interface AuditListParams {
  page?: number;
  pageSize?: number;
  sortOrder?: "asc" | "desc";
  entityType?: AuditEntityType;
  entityId?: string;
  actorId?: string;
  eventType?: AuditEventType;
  startAt?: string;
  endAt?: string;
}
