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
