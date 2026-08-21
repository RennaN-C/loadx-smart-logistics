import type { StatusTone } from "../../../components/StatusPill";
import type { LoadPlanStatus, RejectionReason, RotationCode } from "../types";

export const PLAN_STATUS_LABELS: Record<LoadPlanStatus, string> = {
  CALCULATED: "Calculado",
  APPROVED: "Aprovado",
  REJECTED: "Recusado",
};

export function planStatusTone(status: LoadPlanStatus): StatusTone {
  if (status === "APPROVED") return "good";
  if (status === "REJECTED") return "neutral";
  return "warn";
}

/**
 * Explica por que o volume ficou de fora. É o texto que o usuário usa para
 * decidir o que fazer — trocar de caminhão, tirar um pedido ou revisar o
 * cadastro do produto —, então não basta repetir o código do backend.
 */
export const REJECTION_LABELS: Record<RejectionReason, string> = {
  TRUCK_DIMENSIONS_EXCEEDED: "Não cabe nas medidas do baú",
  TRUCK_WEIGHT_EXCEEDED: "Estouraria o peso máximo do caminhão",
  NON_STACKABLE_SUPPORT: "A base disponível não aceita empilhamento",
  FRAGILE_SUPPORT_WEIGHT_EXCEEDED: "Peso demais sobre um volume frágil",
  INSUFFICIENT_SUPPORT: "Apoio insuficiente na base",
  COLLISION: "Colidiria com outro volume",
  NO_VALID_POSITION: "Sem posição livre que atenda às regras",
};

/** Ordem em que os eixos do volume foram usados; XYZ é o volume sem girar. */
export const ROTATION_LABELS: Record<RotationCode, string> = {
  XYZ: "Sem rotação",
  XZY: "Deitado no comprimento",
  YXZ: "Girado de lado",
  YZX: "De lado e deitado",
  ZXY: "Em pé no comprimento",
  ZYX: "Girado e em pé",
};
