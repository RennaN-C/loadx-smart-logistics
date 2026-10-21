import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";

export interface LoadingListItem {
  id: string;
  loadPlanId: string;
  status: string;
  startedAt: string | null;
  finishedAt: string | null;
}
export interface DeliveryListItem {
  id: string;
  tripId: string;
  orderId: string;
  status: string;
  sequence: number;
  deliveredAt: string | null;
}
interface LoadingDto {
  id: string;
  load_plan_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
}
interface DeliveryDto {
  id: string;
  trip_id: string;
  order_id: string;
  status: string;
  sequence: number;
  delivered_at: string | null;
}

export async function listLoadingSessions(params: ListParams & { status?: string } = {}): Promise<Page<LoadingListItem>> {
  const { data } = await api.get<PageDto<LoadingDto>>("/loading-sessions", { params: { ...toPageQuery(params), status: params.status } });
  return mapPageFromDto(data, (dto) => ({
    id: dto.id,
    loadPlanId: dto.load_plan_id,
    status: dto.status,
    startedAt: dto.started_at,
    finishedAt: dto.finished_at,
  }));
}

export async function listDeliveries(params: ListParams & { status?: string } = {}): Promise<Page<DeliveryListItem>> {
  const { data } = await api.get<PageDto<DeliveryDto>>("/deliveries", { params: { ...toPageQuery(params), status: params.status } });
  return mapPageFromDto(data, (dto) => ({
    id: dto.id,
    tripId: dto.trip_id,
    orderId: dto.order_id,
    status: dto.status,
    sequence: dto.sequence,
    deliveredAt: dto.delivered_at,
  }));
}
