import { api } from "../../../services/api";
import {
  mapPageFromDto,
  toPageQuery,
  type ListParams,
  type PageDto,
} from "../../../services/pagination";
import { requestProtectedBlob } from "../../../services/protectedDownload";
import type { Page } from "../../../types/api";
import type { DeliveryEvidence, DeliveryReceipt, EvidenceKind } from "../types";

/**
 * Comprovante da entrega (OC78) e evidências ligadas a ele (OC80).
 *
 * São dois contratos encadeados: o comprovante nasce da CONCLUSÃO da entrega e
 * só existe depois dela; a evidência se pendura nesse comprovante. Por isso a
 * tela pede o comprovante primeiro — sem ele não há onde anexar nada, e o
 * backend responde `DELIVERY_RECEIPT_NOT_AVAILABLE`.
 */

interface ReceiptDto {
  id: string;
  delivery_id: string;
  trip_id: string;
  order_id: string;
  driver_id: string;
  delivered_at: string;
  recorded_at: string;
  recorded_by: string;
}

interface EvidenceDto {
  id: string;
  delivery_id: string;
  receipt_id: string;
  kind: EvidenceKind;
  media_type: "image/png" | "image/jpeg";
  size_bytes: number;
  sha256: string;
  status: "ACTIVE" | "REVOKED";
  recorded_by: string;
  recorded_at: string;
  revoked_by: string | null;
  revoked_at: string | null;
}

function mapReceipt(dto: ReceiptDto): DeliveryReceipt {
  return {
    id: dto.id,
    deliveryId: dto.delivery_id,
    tripId: dto.trip_id,
    orderId: dto.order_id,
    driverId: dto.driver_id,
    deliveredAt: dto.delivered_at,
    recordedAt: dto.recorded_at,
    recordedBy: dto.recorded_by,
  };
}

function mapEvidence(dto: EvidenceDto): DeliveryEvidence {
  return {
    id: dto.id,
    deliveryId: dto.delivery_id,
    receiptId: dto.receipt_id,
    kind: dto.kind,
    mediaType: dto.media_type,
    sizeBytes: dto.size_bytes,
    sha256: dto.sha256,
    status: dto.status,
    recordedBy: dto.recorded_by,
    recordedAt: dto.recorded_at,
    revokedBy: dto.revoked_by,
    revokedAt: dto.revoked_at,
  };
}

const base = (deliveryId: string) => `/deliveries/${encodeURIComponent(deliveryId)}`;

/** Consulta; não registra conclusão. `POST` do comprovante é do fluxo de status. */
export async function getDeliveryReceipt(deliveryId: string): Promise<DeliveryReceipt> {
  const { data } = await api.get<ReceiptDto>(`${base(deliveryId)}/receipt`);

  return mapReceipt(data);
}

export async function listDeliveryEvidences(
  deliveryId: string,
  params: ListParams = {},
): Promise<Page<DeliveryEvidence>> {
  const { data } = await api.get<PageDto<EvidenceDto>>(`${base(deliveryId)}/evidences`, {
    params: toPageQuery(params),
  });

  return mapPageFromDto(data, mapEvidence);
}

/**
 * Registra uma evidência.
 *
 * `eventId` é a chave de intenção, e quem chama precisa REAPROVEITÁ-LA no
 * retry dos mesmos bytes: o backend tem UNIQUE (recorded_by, event_id) e
 * devolve o registro original em vez de duplicar. Gerar uma chave nova a cada
 * tentativa transformaria uma falha de rede em duas evidências iguais.
 */
export async function registerDeliveryEvidence(
  deliveryId: string,
  input: { eventId: string; kind: EvidenceKind; contentBase64: string },
): Promise<DeliveryEvidence> {
  const { data } = await api.post<EvidenceDto>(`${base(deliveryId)}/evidences`, {
    event_id: input.eventId,
    kind: input.kind,
    content_base64: input.contentBase64,
  });

  return mapEvidence(data);
}

/** Revogação lógica e idempotente: preserva metadados e bloqueia o download. */
export async function revokeDeliveryEvidence(
  deliveryId: string,
  evidenceId: string,
): Promise<DeliveryEvidence> {
  const { data } = await api.post<EvidenceDto>(
    `${base(deliveryId)}/evidences/${encodeURIComponent(evidenceId)}/revoke`,
    {},
  );

  return mapEvidence(data);
}

/** Só evidência `ACTIVE` baixa; o nome do arquivo é definido pelo servidor. */
export async function downloadDeliveryEvidence(
  deliveryId: string,
  evidenceId: string,
): Promise<Blob> {
  return requestProtectedBlob(
    `${base(deliveryId)}/evidences/${encodeURIComponent(evidenceId)}/content`,
    "Não foi possível baixar a evidência.",
  );
}
