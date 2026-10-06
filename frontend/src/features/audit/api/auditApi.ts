import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type {
  AuditEntry,
  AuditEntityType,
  AuditEventType,
  AuditListParams,
} from "../types";

interface AuditEntryDto {
  id: string;
  event_type: AuditEventType;
  entity_type: AuditEntityType;
  entity_id: string;
  actor_id: string | null;
  actor_name: string | null;
  old_status: string | null;
  new_status: string | null;
  changed_fields: string[];
  created_at: string;
}

export function mapAuditEntryFromDto(dto: AuditEntryDto): AuditEntry {
  return {
    id: dto.id,
    eventType: dto.event_type,
    entityType: dto.entity_type,
    entityId: dto.entity_id,
    actorId: dto.actor_id,
    actorName: dto.actor_name,
    oldStatus: dto.old_status,
    newStatus: dto.new_status,
    changedFields: dto.changed_fields,
    createdAt: dto.created_at,
  };
}

export async function listAuditEntries(
  params: AuditListParams = {},
): Promise<Page<AuditEntry>> {
  const query: Record<string, string | number> = toPageQuery({
    page: params.page,
    pageSize: params.pageSize,
    sortOrder: params.sortOrder,
  });

  if (params.entityType) query.entity_type = params.entityType;
  if (params.entityId) query.entity_id = params.entityId;
  if (params.actorId) query.actor_id = params.actorId;
  if (params.eventType) query.event_type = params.eventType;
  if (params.startAt) query.start_at = params.startAt;
  if (params.endAt) query.end_at = params.endAt;

  const { data } = await api.get<PageDto<AuditEntryDto>>("/audit", { params: query });
  return mapPageFromDto(data, mapAuditEntryFromDto);
}
