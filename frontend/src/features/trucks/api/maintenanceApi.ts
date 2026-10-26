import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type { MaintenanceCloseInput, MaintenanceInput, TruckMaintenance } from "../types";
interface MaintenanceDto {
  id: string; truck_id: string; kind: TruckMaintenance["kind"]; starts_at: string;
  ends_at: string | null; description: string; workshop: string | null; notes: string | null;
  cost: number | null; odometer_km: number | null; completion_odometer_km: number | null;
  next_service_at: string | null; next_service_km: number | null; closed_at: string | null; created_at: string;
}
function fromDto(dto: MaintenanceDto): TruckMaintenance {
  return { id: dto.id, truckId: dto.truck_id, kind: dto.kind, startsAt: dto.starts_at, endsAt: dto.ends_at, description: dto.description, workshop: dto.workshop, notes: dto.notes, cost: dto.cost, odometerKm: dto.odometer_km, completionOdometerKm: dto.completion_odometer_km, nextServiceAt: dto.next_service_at, nextServiceKm: dto.next_service_km, closedAt: dto.closed_at, createdAt: dto.created_at };
}
export async function listMaintenances(truckId: string, params: ListParams = {}): Promise<Page<TruckMaintenance>> {
  const { data } = await api.get<PageDto<MaintenanceDto>>(`/trucks/${truckId}/maintenances`, { params: toPageQuery(params) });
  return mapPageFromDto(data, fromDto);
}
export async function createMaintenance(truckId: string, input: MaintenanceInput): Promise<TruckMaintenance> {
  const { data } = await api.post<MaintenanceDto>(`/trucks/${truckId}/maintenances`, { kind: input.kind, starts_at: input.startsAt, ends_at: input.endsAt, description: input.description, workshop: input.workshop, notes: input.notes, cost: input.cost, odometer_km: input.odometerKm });
  return fromDto(data);
}
export async function closeMaintenance(truckId: string, id: string, input: MaintenanceCloseInput): Promise<TruckMaintenance> {
  const { data } = await api.post<MaintenanceDto>(`/trucks/${truckId}/maintenances/${id}/close`, { odometer_km: input.odometerKm, ...(input.nextServiceAt !== undefined ? { next_service_at: input.nextServiceAt } : {}), ...(input.nextServiceKm !== undefined ? { next_service_km: input.nextServiceKm } : {}) });
  return fromDto(data);
}
