import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
export type SimulationStatus = "NOT_ATTEMPTED" | "ATTEMPT_CLAIMED" | "SIMULATED" | "FAILED" | "NO_RECIPIENT";
export type ProcessingStatus = "PENDING" | "PROCESSING" | "SUCCEEDED" | "RETRYABLE" | "TERMINAL" | "UNCERTAIN";
export interface DeliveryCommunication {
  id: string;
  occurrence_id: string;
  event_type: "OCCURRENCE_REGISTERED";
  created_at: string;
  channel: "WHATSAPP_MOCK";
  simulation_status: SimulationStatus;
  processing_status: ProcessingStatus | null;
}
/** Somente fatos que o servidor vincula à entrega, sem varrer a caixa pessoal. */
export async function listDeliveryCommunications(deliveryId: string, params: ListParams = {}): Promise<Page<DeliveryCommunication>> {
  const { data } = await api.get<PageDto<DeliveryCommunication>>(`/deliveries/${encodeURIComponent(deliveryId)}/communications`, { params: toPageQuery(params) });
  return mapPageFromDto(data, row => row);
}
