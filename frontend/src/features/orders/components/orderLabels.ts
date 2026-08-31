import type { StatusTone } from "../../../components/StatusPill";
import type { OrderPriority, OrderStatus } from "../types";

export const STATUS_LABELS: Record<OrderStatus, string> = {
  DRAFT: "Rascunho",
  READY: "Pronto",
  PLANNED: "Planejado",
  IN_TRANSIT: "Em trânsito",
  DELIVERED: "Entregue",
  CANCELED: "Cancelado",
};

export const PRIORITY_LABELS: Record<OrderPriority, string> = {
  LOW: "Baixa",
  NORMAL: "Normal",
  HIGH: "Alta",
  URGENT: "Urgente",
};

export function priorityLabel(priority: OrderPriority): string {
  return PRIORITY_LABELS[priority] ?? priority;
}

/**
 * Numa grade de cartões, prioridade escrita em texto igual ao resto passa
 * batido. Alta e urgente ganham destaque; o resto continua discreto, senão o
 * destaque deixa de destacar.
 */
export function priorityIsUrgent(priority: OrderPriority): boolean {
  return priority === "HIGH" || priority === "URGENT";
}

export function statusTone(status: OrderStatus): StatusTone {
  if (status === "DELIVERED") return "good";
  if (status === "CANCELED") return "neutral";
  return "warn";
}
