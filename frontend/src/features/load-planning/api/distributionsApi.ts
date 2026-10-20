import { api } from "../../../services/api";
import { mapLoadPlanFromDto, type LoadPlanDto } from "./loadPlansApi";
import type { DistributionNeed, DistributionPartStatus, DistributionStatus, IneligibleTruckReason, LoadDistribution, TruckSnapshot } from "../types";

interface TruckDto {
  id: string; plate: string; model: string; width_cm: number;
  height_cm: number; length_cm: number; max_weight_kg: number;
}
export interface DistributionDto {
  id: string; status: DistributionStatus; created_by: string; created_at: string;
  order_ids: string[]; truck_count: number; volume_count: number;
  parts: { id: string; status: DistributionPartStatus; truck: TruckDto; load_plan: LoadPlanDto }[];
  volumes: { order_item_id: string; volume_index: number; order_id: string;
    product_id: string; quantity: number; part_id: string }[];
}
export interface DistributionNeedDto {
  order_ids: string[];
  volumes: { order_item_id: string; volume_index: number; order_id: string;
    product_id: string; width_cm: number; height_cm: number; length_cm: number;
    weight_kg: number; delivery_sequence: number; fragile: boolean; stackable: boolean; rotation_allowed: boolean }[];
  eligible_trucks: TruckDto[];
  ineligible_trucks: { truck_id: string; reason: IneligibleTruckReason }[];
}
function mapTruck(dto: TruckDto): TruckSnapshot {
  return { id: dto.id, plate: dto.plate, model: dto.model, widthCm: dto.width_cm,
    heightCm: dto.height_cm, lengthCm: dto.length_cm, maxWeightKg: dto.max_weight_kg };
}
export function mapDistribution(dto: DistributionDto): LoadDistribution {
  return { id: dto.id, status: dto.status, createdBy: dto.created_by, createdAt: dto.created_at,
    orderIds: dto.order_ids, truckCount: dto.truck_count, volumeCount: dto.volume_count,
    parts: dto.parts.map((part) => ({ id: part.id, status: part.status,
      truck: mapTruck(part.truck), loadPlan: mapLoadPlanFromDto(part.load_plan) })),
    volumes: dto.volumes.map((v) => ({ orderItemId: v.order_item_id, volumeIndex: v.volume_index,
      orderId: v.order_id, productId: v.product_id, quantity: v.quantity, partId: v.part_id })) };
}
export async function preflightDistribution(orderIds: string[]): Promise<DistributionNeed> {
  const { data } = await api.post<DistributionNeedDto>("/load-distributions/preflight", { order_ids: orderIds });
  return { orderIds: data.order_ids,
    eligibleTrucks: data.eligible_trucks.map(mapTruck),
    ineligibleTrucks: data.ineligible_trucks.map((t) => ({ truckId: t.truck_id, reason: t.reason })),
    volumes: data.volumes.map((v) => ({ orderItemId: v.order_item_id, volumeIndex: v.volume_index,
      orderId: v.order_id, productId: v.product_id, widthCm: v.width_cm, heightCm: v.height_cm,
      lengthCm: v.length_cm, weightKg: v.weight_kg, deliverySequence: v.delivery_sequence,
      fragile: v.fragile, stackable: v.stackable, rotationAllowed: v.rotation_allowed })) };
}
export async function optimizeDistribution(orderIds: string[]): Promise<LoadDistribution> {
  const { data } = await api.post<DistributionDto>("/load-distributions/optimize", { order_ids: orderIds });
  return mapDistribution(data);
}
export async function getDistribution(id: string): Promise<LoadDistribution> {
  const { data } = await api.get<DistributionDto>(`/load-distributions/${id}`);
  return mapDistribution(data);
}
export async function distributionAction(id: string, action: "approve" | "cancel", partId?: string): Promise<LoadDistribution> {
  const path = partId ? `/parts/${partId}` : "";
  const { data } = await api.post<DistributionDto>(`/load-distributions/${id}${path}/${action}`, {});
  return mapDistribution(data);
}
export async function reprocessDistributionPart(id: string, partId: string, truckId: string, expectedLoadPlanId: string): Promise<LoadDistribution> {
  const { data } = await api.post<DistributionDto>(`/load-distributions/${id}/parts/${partId}/reprocess`, {
    truck_id: truckId, expected_load_plan_id: expectedLoadPlanId,
  });
  return mapDistribution(data);
}
