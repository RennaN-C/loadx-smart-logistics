export const TRIP_STATUSES = ["SCHEDULED", "IN_ROUTE", "FINISHED"] as const;
export type TripStatus = (typeof TRIP_STATUSES)[number];

export const DELIVERY_STATUSES = ["PENDING", "IN_DELIVERY", "DELIVERED"] as const;
export type DeliveryStatus = (typeof DELIVERY_STATUSES)[number];

/**
 * Ciclos são de mão única no backend (TRIP_STATUS_TRANSITIONS e
 * DELIVERY_STATUS_TRANSITIONS): não existe voltar atrás nem pular etapa.
 */
export const TRIP_TRANSITIONS: Partial<Record<TripStatus, TripStatus>> = {
  SCHEDULED: "IN_ROUTE",
  IN_ROUTE: "FINISHED",
};

export const DELIVERY_TRANSITIONS: Partial<Record<DeliveryStatus, DeliveryStatus>> = {
  PENDING: "IN_DELIVERY",
  IN_DELIVERY: "DELIVERED",
};

export interface Delivery {
  id: string;
  tripId: string;
  orderId: string;
  status: DeliveryStatus;
  /** Ordem da parada na rota. */
  sequence: number;
  deliveredAt: string | null;
}

export interface Trip {
  id: string;
  loadPlanId: string;
  driverId: string;
  status: TripStatus;
  startedAt: string | null;
  finishedAt: string | null;
  deliveries: Delivery[];
}

export interface TripInput {
  loadPlanId: string;
  driverId: string;
}
