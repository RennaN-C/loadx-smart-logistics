export const TRIP_STATUSES = ["SCHEDULED", "IN_ROUTE", "INTERRUPTED", "FINISHED", "CANCELED"] as const;
export type TripStatus = (typeof TRIP_STATUSES)[number];

export const DELIVERY_STATUSES = ["PENDING", "IN_DELIVERY", "DELIVERED", "CANCELED"] as const;
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

/**
 * O que `GET /trips` devolve por item. É um resumo: sem as entregas, só a
 * contagem delas — quem precisa da rota abre `GET /trips/{id}`.
 */
export interface TripListItem {
  id: string;
  loadPlanId: string;
  driverId: string;
  status: TripStatus;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string;
  deliveryCount: number;
}

export interface TripInput {
  loadPlanId: string;
  driverId: string;
}

/**
 * Comprovante da conclusão (OC78). `id` identifica o HISTÓRICO da conclusão,
 * não um arquivo: o comprovante não tem imagem nem assinatura embutida.
 */
export interface DeliveryReceipt {
  id: string;
  deliveryId: string;
  tripId: string;
  orderId: string;
  driverId: string;
  /** Quando a entrega aconteceu. */
  deliveredAt: string;
  /** Quando a conclusão foi registrada — horário distinto do anterior. */
  recordedAt: string;
  recordedBy: string;
}

export type EvidenceKind = "PHOTO" | "SIGNATURE";

/**
 * Evidência pendurada no comprovante (OC80). O backend nunca devolve os bytes
 * aqui: a imagem só sai pelo download autenticado, e só enquanto `ACTIVE`.
 */
export interface DeliveryEvidence {
  id: string;
  deliveryId: string;
  receiptId: string;
  kind: EvidenceKind;
  mediaType: "image/png" | "image/jpeg";
  sizeBytes: number;
  sha256: string;
  status: "ACTIVE" | "REVOKED";
  recordedBy: string;
  recordedAt: string;
  revokedBy: string | null;
  revokedAt: string | null;
}

export const EVIDENCE_KIND_LABELS: Record<EvidenceKind, string> = {
  PHOTO: "Foto",
  SIGNATURE: "Assinatura",
};
