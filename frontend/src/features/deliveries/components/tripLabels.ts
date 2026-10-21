import type { StatusTone } from "../../../components/StatusPill";
import type { DeliveryStatus, TripStatus } from "../types";

export const TRIP_STATUS_LABELS: Record<TripStatus, string> = {
  SCHEDULED: "Agendada",
  IN_ROUTE: "Em rota",
  FINISHED: "Finalizada",
  CANCELED: "Cancelada",
};

export const DELIVERY_STATUS_LABELS: Record<DeliveryStatus, string> = {
  PENDING: "Pendente",
  IN_DELIVERY: "Em entrega",
  DELIVERED: "Entregue",
  CANCELED: "Cancelada",
};

/** Texto do botão que avança o ciclo — o verbo diz o que acontece, não o estado. */
export const TRIP_ACTION_LABELS: Record<TripStatus, string> = {
  SCHEDULED: "Iniciar viagem",
  IN_ROUTE: "Finalizar viagem",
  FINISHED: "Finalizada",
  CANCELED: "Cancelada",
};

export const DELIVERY_ACTION_LABELS: Record<DeliveryStatus, string> = {
  PENDING: "Iniciar entrega",
  IN_DELIVERY: "Confirmar entrega",
  DELIVERED: "Entregue",
  CANCELED: "Cancelada",
};

export function tripStatusTone(status: TripStatus): StatusTone {
  if (status === "FINISHED") return "good";
  if (status === "CANCELED") return "neutral";
  if (status === "SCHEDULED") return "neutral";
  return "warn";
}

export function deliveryStatusTone(status: DeliveryStatus): StatusTone {
  if (status === "DELIVERED") return "good";
  if (status === "CANCELED") return "neutral";
  if (status === "PENDING") return "neutral";
  return "warn";
}
