import type { TripStatus } from "../deliveries/types";

export const LOAD_PLAN_STATUSES = ["CALCULATED", "APPROVED", "REJECTED"] as const;
export type LoadPlanStatus = (typeof LOAD_PLAN_STATUSES)[number];

/** Ordem dos eixos aplicada ao girar o volume (x=largura, y=altura, z=comprimento). */
export const ROTATION_CODES = ["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"] as const;
export type RotationCode = (typeof ROTATION_CODES)[number];

export const REJECTION_REASONS = [
  "TRUCK_DIMENSIONS_EXCEEDED",
  "TRUCK_WEIGHT_EXCEEDED",
  "NON_STACKABLE_SUPPORT",
  "FRAGILE_SUPPORT_WEIGHT_EXCEEDED",
  "INSUFFICIENT_SUPPORT",
  "COLLISION",
  "NO_VALID_POSITION",
] as const;
export type RejectionReason = (typeof REJECTION_REASONS)[number];

/** Campos que todo item carrega, colocado ou não: o retrato do produto no momento do cálculo. */
interface LoadPlanItemSnapshot {
  id: string;
  orderId: string;
  orderItemId: string;
  productId: string;
  /** Qual unidade do item este volume representa (quantity > 1 vira vários volumes). */
  volumeIndex: number;
  quantity: number;
  deliverySequence: number;
  productCode: string;
  productName: string;
  originalWidthCm: number;
  originalHeightCm: number;
  originalLengthCm: number;
  weightKg: number;
  fragile: boolean;
  stackable: boolean;
  rotationAllowed: boolean;
}

export interface LoadPlanItem extends LoadPlanItemSnapshot {
  /** Posição no baú, origem no piso frente-esquerda. Null quando não coube. */
  xCm: number | null;
  yCm: number | null;
  zCm: number | null;
  /** Dimensões DEPOIS da rotação aplicada. */
  widthCm: number | null;
  heightCm: number | null;
  lengthCm: number | null;
  rotationCode: RotationCode | null;
  loadingSequence: number | null;
  placed: boolean;
  rejectionReason: RejectionReason | null;
}

export interface LoadPlan {
  ordersReadyForApproval?: boolean | null;
  distributionId?: string | null;
  distributionStatus?: DistributionStatus | null;
  partStatus?: DistributionPartStatus | null;
  isCurrentPart?: boolean;
  id: string;
  truckId: string;
  /** Preenchido quando este plano nasceu de um recálculo de outro. */
  recalculatedFromId: string | null;
  status: LoadPlanStatus;
  internalVolumeCm3: number;
  usedVolumeCm3: number;
  occupancyPercent: number;
  totalWeightKg: number;
  loadedCount: number;
  unloadedCount: number;
  algorithmVersion: string;
  createdAt: string;
  approvedAt: string | null;
  orderIds: string[];
  items: LoadPlanItem[];
}

export interface LoadPlanInput {
  truckId: string;
  orderIds: string[];
}

/* ---- visualização (OC31): mesmo plano, já separado em colocados e recusados ---- */

export interface TruckSnapshot {
  id: string;
  plate: string;
  model: string;
  widthCm: number;
  heightCm: number;
  lengthCm: number;
  maxWeightKg: number;
}

export interface PlacedItem extends LoadPlanItemSnapshot {
  xCm: number;
  yCm: number;
  zCm: number;
  widthCm: number;
  heightCm: number;
  lengthCm: number;
  rotationCode: RotationCode;
  loadingSequence: number;
}

export interface UnloadedItem extends LoadPlanItemSnapshot {
  rejectionReason: RejectionReason;
}

export interface LoadPlanVisualization {
  truck: TruckSnapshot;
  items: PlacedItem[];
  unloadedItems: UnloadedItem[];
}

export type PlanOperationStatus = "NOT_STARTED" | "IN_PROGRESS" | "PARTIALLY_DELIVERED" | "COMPLETED" | "INCOMPLETE" | "CANCELED";
export interface PlanOperation {
  status: PlanOperationStatus;
  loading_session_id: string | null;
  loading_status: "PENDING" | "IN_PROGRESS" | "FINISHED" | null;
  trip_id: string | null;
  trip_status: TripStatus | null;
  order_count: number;
  delivered_order_count: number;
  partial_order_count: number;
  ready_order_count: number;
  delivery_count: number;
  delivered_leg_count: number;
}

export interface LoadPlanListItem {
  operation?: PlanOperation | null;
  distributionId?: string | null;
  distributionStatus?: DistributionStatus | null;
  partStatus?: DistributionPartStatus | null;
  isCurrentPart?: boolean;
  id: string;
  truckId: string;
  truckPlate: string;
  truckModel: string;
  status: LoadPlanStatus;
  createdAt: string;
  recalculatedFromId: string | null;
  loadedCount: number;
  unloadedCount: number;
  occupancyPercent: number;
  totalWeightKg: number;
  orderCount: number;
}

export interface LoadPlanContinuity {
  operation?: PlanOperation | null;
  loading_session: { id: string; status: "PENDING" | "IN_PROGRESS" | "FINISHED" } | null;
  trip: { id: string; status: TripStatus } | null;
  operational_ready: boolean;
}


export type DistributionStatus = "PROPOSED" | "PARTIALLY_APPROVED" | "APPROVED" | "INCOMPLETE" | "CANCELED";
export type DistributionPartStatus = "PENDING" | "APPROVED" | "CANCELED";
export interface VolumeReference { orderItemId: string; volumeIndex: number }
export interface DistributionVolume extends VolumeReference {
  orderId: string; productId: string; quantity: number; partId: string;
}
export interface DistributionPart {
  id: string; status: DistributionPartStatus; truck: TruckSnapshot; loadPlan: LoadPlan;
}
export interface LoadDistribution {
  id: string; status: DistributionStatus; createdBy: string; createdAt: string;
  orderIds: string[]; truckCount: number; volumeCount: number;
  parts: DistributionPart[]; volumes: DistributionVolume[];
}
export type IneligibleTruckReason = "INACTIVE" | "TRUCK_OPERATION_CONFLICT" | "TRUCK_IN_MAINTENANCE" | "TRUCK_DOCUMENT_INELIGIBLE";
export interface DistributionNeed {
  orderIds: string[];
  volumes: (VolumeReference & { orderId: string; productId: string; widthCm: number;
    heightCm: number; lengthCm: number; weightKg: number; deliverySequence: number;
    fragile: boolean; stackable: boolean; rotationAllowed: boolean })[];
  eligibleTrucks: TruckSnapshot[];
  ineligibleTrucks: { truckId: string; reason: IneligibleTruckReason }[];
}
