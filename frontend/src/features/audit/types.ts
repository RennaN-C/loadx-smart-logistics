export const AUDIT_ENTITY_TYPES = ["ORDER", "LOAD_PLAN", "TRIP", "DELIVERY", "USER", "LOAD_DISTRIBUTION", "LOAD_DISTRIBUTION_PART", "CUSTOMER", "CUSTOMER_ADDRESS", "TRUCK_MAINTENANCE", "TRUCK_DOCUMENT", "TRUCK_DOCUMENT_POLICY", "DRIVER_DOCUMENT", "DRIVER_DOCUMENT_POLICY", "DRIVER_DOCUMENT_TYPE", "PRODUCT", "TRUCK", "DRIVER"] as const;
export type AuditEntityType = (typeof AUDIT_ENTITY_TYPES)[number];

export const AUDIT_EVENT_TYPES = ["STATUS_CHANGED", "USER_CREATED", "USER_UPDATED", "RECORD_ARCHIVED", "RECORD_REACTIVATED", "CUSTOMER_ADDRESS_CREATED", "CUSTOMER_ADDRESS_UPDATED", "CUSTOMER_ADDRESS_ARCHIVED", "CUSTOMER_ADDRESS_REACTIVATED", "MAINTENANCE_CREATED", "MAINTENANCE_CLOSED", "TRUCK_ODOMETER_UPDATED", "TRUCK_DOCUMENT_CREATED", "TRUCK_DOCUMENT_RENEWED", "TRUCK_DOCUMENT_POLICY_UPDATED", "DRIVER_DOCUMENT_CREATED", "DRIVER_DOCUMENT_RENEWED", "DRIVER_DOCUMENT_POLICY_UPDATED", "DRIVER_DOCUMENT_TYPE_APPROVED"] as const;
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
