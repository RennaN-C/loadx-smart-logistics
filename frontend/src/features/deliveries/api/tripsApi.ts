import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type {
  Delivery,
  DeliveryStatus,
  Trip,
  TripInput,
  TripListItem,
  TripStatus,
} from "../types";

interface DeliveryDto {
  id: string;
  trip_id: string;
  order_id: string;
  status: DeliveryStatus;
  sequence: number;
  delivered_at: string | null;
}

interface TripDto {
  id: string;
  load_plan_id: string;
  driver_id: string;
  status: TripStatus;
  started_at: string | null;
  finished_at: string | null;
  deliveries: DeliveryDto[];
}

interface TripListDto {
  id: string;
  load_plan_id: string;
  driver_id: string;
  status: TripStatus;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  delivery_count: number;
}

function mapTripListItem(dto: TripListDto): TripListItem {
  return {
    id: dto.id,
    loadPlanId: dto.load_plan_id,
    driverId: dto.driver_id,
    status: dto.status,
    startedAt: dto.started_at,
    finishedAt: dto.finished_at,
    createdAt: dto.created_at,
    deliveryCount: dto.delivery_count,
  };
}

/**
 * `GET /trips`, paginado. `ADMIN` e `LOGISTICS_MANAGER` veem todas as viagens;
 * `DRIVER` recebe SOMENTE as dele — o recorte é feito no backend
 * (`deliveries/service.py`), não aqui.
 */
export async function listTrips(params: ListParams = {}): Promise<Page<TripListItem>> {
  const { data } = await api.get<PageDto<TripListDto>>("/trips", { params: toPageQuery(params) });

  return mapPageFromDto(data, mapTripListItem);
}

function mapDelivery(dto: DeliveryDto): Delivery {
  return {
    id: dto.id,
    tripId: dto.trip_id,
    orderId: dto.order_id,
    status: dto.status,
    sequence: dto.sequence,
    deliveredAt: dto.delivered_at,
  };
}

export function mapTripFromDto(dto: TripDto): Trip {
  return {
    id: dto.id,
    loadPlanId: dto.load_plan_id,
    driverId: dto.driver_id,
    status: dto.status,
    startedAt: dto.started_at,
    finishedAt: dto.finished_at,
    deliveries: dto.deliveries.map(mapDelivery),
  };
}

export async function createTrip(input: TripInput): Promise<Trip> {
  const { data } = await api.post<TripDto>("/trips", {
    load_plan_id: input.loadPlanId,
    driver_id: input.driverId,
  });

  return mapTripFromDto(data);
}

export async function getTrip(id: string): Promise<Trip> {
  const { data } = await api.get<TripDto>(`/trips/${id}`);

  return mapTripFromDto(data);
}

export async function changeTripStatus(id: string, status: TripStatus): Promise<Trip> {
  const { data } = await api.patch<TripDto>(`/trips/${id}/status`, { status });

  return mapTripFromDto(data);
}

/** Devolve a viagem inteira: a entrega alterada não vem sozinha. */
export async function changeDeliveryStatus(id: string, status: DeliveryStatus): Promise<Trip> {
  const { data } = await api.patch<TripDto>(`/deliveries/${id}/status`, { status });

  return mapTripFromDto(data);
}
