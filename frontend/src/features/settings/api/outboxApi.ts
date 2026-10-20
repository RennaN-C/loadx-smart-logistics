import { api } from "../../../services/api";
import { mapPageFromDto, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";

export type OutboxState = "PENDING" | "PROCESSING" | "SUCCEEDED" | "RETRYABLE" | "TERMINAL" | "UNCERTAIN";
export type OutboxType = "TRIP_STARTED" | "OCCURRENCE_REGISTERED";
export interface OutboxEvent {
  id: string; notification_id: string; channel: "WHATSAPP_MOCK"; event_type: OutboxType;
  contract_version: 1; correlation_id: string; status: OutboxState;
  attempt_count: number; generation: number; next_attempt_at: string;
  lease_expires_at: string | null; last_error_code: string | null;
  created_at: string; updated_at: string;
}
export interface OutboxAttempt {
  id: string; generation: number; origin: "LEGACY" | "WORKER";
  started_at: string; finished_at: string | null; result: OutboxState; error_code: string | null;
}
export interface OutboxSummary { counts: Record<OutboxState, number>; oldest_pending_at: string | null }
export interface OutboxFilters { page: number; page_size?: number; status?: OutboxState; event_type?: OutboxType; sort_order?: "asc" | "desc" }
const path = (id: string) => `/outbox-events/${encodeURIComponent(id)}`;
export async function listOutbox(filters: OutboxFilters, signal?: AbortSignal): Promise<Page<OutboxEvent>> {
  const { data } = await api.get<PageDto<OutboxEvent>>("/outbox-events", { params: filters, signal, timeout: 8000 });
  return mapPageFromDto(data, (item) => item);
}
export async function getOutboxSummary(signal?: AbortSignal): Promise<OutboxSummary> {
  const { data } = await api.get<OutboxSummary>("/outbox-events/summary", { signal, timeout: 8000 });
  return data;
}
export async function getOutboxEvent(id: string, signal?: AbortSignal): Promise<OutboxEvent> {
  const { data } = await api.get<OutboxEvent>(path(id), { signal, timeout: 8000 }); return data;
}
export async function getOutboxAttempts(id: string, page: number, signal?: AbortSignal): Promise<Page<OutboxAttempt>> {
  const { data } = await api.get<PageDto<OutboxAttempt>>(`${path(id)}/attempts`, { params: { page, page_size: 10 }, signal, timeout: 8000 });
  return mapPageFromDto(data, (item) => item);
}
export async function retryOutbox(id: string, commandId: string): Promise<OutboxEvent> {
  const { data } = await api.post<OutboxEvent>(`${path(id)}/retry`, { command_id: commandId }, { timeout: 8000 }); return data;
}
export async function getOutboxSource(id: string): Promise<string> {
  const { data } = await api.get<{ href: string }>(`${path(id)}/source`, { timeout: 8000 }); return data.href;
}
