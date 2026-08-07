import { api } from "../../../services/api";
import type {
  LoadPlan,
  LoadPlanInput,
  LoadPlanItem,
  LoadPlanStatus,
  LoadPlanVisualization,
  PlacedItem,
  RejectionReason,
  RotationCode,
  TruckSnapshot,
  UnloadedItem,
} from "../types";

interface ItemSnapshotDto {
  id: string;
  order_id: string;
  order_item_id: string;
  product_id: string;
  volume_index: number;
  quantity: number;
  delivery_sequence: number;
  product_code: string;
  product_name: string;
  original_width_cm: number;
  original_height_cm: number;
  original_length_cm: number;
  weight_kg: number;
  fragile: boolean;
  stackable: boolean;
  rotation_allowed: boolean;
}

interface LoadPlanItemDto extends ItemSnapshotDto {
  x_cm: number | null;
  y_cm: number | null;
  z_cm: number | null;
  width_cm: number | null;
  height_cm: number | null;
  length_cm: number | null;
  rotation_code: RotationCode | null;
  loading_sequence: number | null;
  placed: boolean;
  rejection_reason: RejectionReason | null;
}

interface LoadPlanDto {
  id: string;
  truck_id: string;
  recalculated_from_id: string | null;
  status: LoadPlanStatus;
  internal_volume_cm3: number;
  used_volume_cm3: number;
  occupancy_percent: number;
  total_weight_kg: number;
  loaded_count: number;
  unloaded_count: number;
  algorithm_version: string;
  created_at: string;
  approved_at: string | null;
  order_ids: string[];
  items: LoadPlanItemDto[];
}

interface PlacedItemDto extends ItemSnapshotDto {
  x_cm: number;
  y_cm: number;
  z_cm: number;
  width_cm: number;
  height_cm: number;
  length_cm: number;
  rotation_code: RotationCode;
  loading_sequence: number;
}

interface VisualizationDto {
  truck: {
    id: string;
    plate: string;
    model: string;
    width_cm: number;
    height_cm: number;
    length_cm: number;
    max_weight_kg: number;
  };
  items: PlacedItemDto[];
  unloaded_items: (ItemSnapshotDto & { rejection_reason: RejectionReason })[];
}

function mapSnapshot(dto: ItemSnapshotDto) {
  return {
    id: dto.id,
    orderId: dto.order_id,
    orderItemId: dto.order_item_id,
    productId: dto.product_id,
    volumeIndex: dto.volume_index,
    quantity: dto.quantity,
    deliverySequence: dto.delivery_sequence,
    productCode: dto.product_code,
    productName: dto.product_name,
    originalWidthCm: dto.original_width_cm,
    originalHeightCm: dto.original_height_cm,
    originalLengthCm: dto.original_length_cm,
    weightKg: dto.weight_kg,
    fragile: dto.fragile,
    stackable: dto.stackable,
    rotationAllowed: dto.rotation_allowed,
  };
}

function mapItem(dto: LoadPlanItemDto): LoadPlanItem {
  return {
    ...mapSnapshot(dto),
    xCm: dto.x_cm,
    yCm: dto.y_cm,
    zCm: dto.z_cm,
    widthCm: dto.width_cm,
    heightCm: dto.height_cm,
    lengthCm: dto.length_cm,
    rotationCode: dto.rotation_code,
    loadingSequence: dto.loading_sequence,
    placed: dto.placed,
    rejectionReason: dto.rejection_reason,
  };
}

export function mapLoadPlanFromDto(dto: LoadPlanDto): LoadPlan {
  return {
    id: dto.id,
    truckId: dto.truck_id,
    recalculatedFromId: dto.recalculated_from_id,
    status: dto.status,
    internalVolumeCm3: dto.internal_volume_cm3,
    usedVolumeCm3: dto.used_volume_cm3,
    occupancyPercent: dto.occupancy_percent,
    totalWeightKg: dto.total_weight_kg,
    loadedCount: dto.loaded_count,
    unloadedCount: dto.unloaded_count,
    algorithmVersion: dto.algorithm_version,
    createdAt: dto.created_at,
    approvedAt: dto.approved_at,
    orderIds: dto.order_ids,
    items: dto.items.map(mapItem),
  };
}

export function mapVisualizationFromDto(dto: VisualizationDto): LoadPlanVisualization {
  const truck: TruckSnapshot = {
    id: dto.truck.id,
    plate: dto.truck.plate,
    model: dto.truck.model,
    widthCm: dto.truck.width_cm,
    heightCm: dto.truck.height_cm,
    lengthCm: dto.truck.length_cm,
    maxWeightKg: dto.truck.max_weight_kg,
  };

  const items: PlacedItem[] = dto.items.map((item) => ({
    ...mapSnapshot(item),
    xCm: item.x_cm,
    yCm: item.y_cm,
    zCm: item.z_cm,
    widthCm: item.width_cm,
    heightCm: item.height_cm,
    lengthCm: item.length_cm,
    rotationCode: item.rotation_code,
    loadingSequence: item.loading_sequence,
  }));

  const unloadedItems: UnloadedItem[] = dto.unloaded_items.map((item) => ({
    ...mapSnapshot(item),
    rejectionReason: item.rejection_reason,
  }));

  return { truck, items, unloadedItems };
}

export async function createLoadPlan(input: LoadPlanInput): Promise<LoadPlan> {
  const { data } = await api.post<LoadPlanDto>("/load-plans", {
    truck_id: input.truckId,
    order_ids: input.orderIds,
  });

  return mapLoadPlanFromDto(data);
}

export async function getLoadPlan(id: string): Promise<LoadPlan> {
  const { data } = await api.get<LoadPlanDto>(`/load-plans/${id}`);

  return mapLoadPlanFromDto(data);
}

export async function getLoadPlanVisualization(id: string): Promise<LoadPlanVisualization> {
  const { data } = await api.get<VisualizationDto>(`/load-plans/${id}/visualization`);

  return mapVisualizationFromDto(data);
}

/** Aprovar move os pedidos do plano para PLANNED. Recusa se houver item rejeitado. */
export async function approveLoadPlan(id: string): Promise<LoadPlan> {
  const { data } = await api.post<LoadPlanDto>(`/load-plans/${id}/approve`);

  return mapLoadPlanFromDto(data);
}

/** Gera um plano novo a partir deste, refazendo o cálculo com os dados atuais. */
export async function recalculateLoadPlan(id: string): Promise<LoadPlan> {
  const { data } = await api.post<LoadPlanDto>(`/load-plans/${id}/recalculate`);

  return mapLoadPlanFromDto(data);
}
