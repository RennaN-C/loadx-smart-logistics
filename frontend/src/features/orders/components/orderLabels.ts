import type { StatusTone } from "../../../components/StatusPill";
import type { OrderStatus } from "../types";

export const STATUS_LABELS: Record<OrderStatus, string> = {
  DRAFT: "Rascunho",
  READY: "Pronto",
  PLANNED: "Planejado",
  IN_TRANSIT: "Em trânsito",
  DELIVERED: "Entregue",
  CANCELED: "Cancelado",
};

export const PRIORITY_LABELS: Record<string, string> = {
  LOW: "Baixa",
  NORMAL: "Normal",
  HIGH: "Alta",
  URGENT: "Urgente",
};

/** Pedidos vindos de outra origem podem trazer prioridade fora da convenção. */
export function priorityLabel(priority: string): string {
  return PRIORITY_LABELS[priority] ?? priority;
}

export function statusTone(status: OrderStatus): StatusTone {
  if (status === "DELIVERED") return "good";
  if (status === "CANCELED") return "neutral";
  return "warn";
}
