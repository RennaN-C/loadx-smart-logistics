import { readImageAsBase64 } from "../../../services/imageFile";
import { requestProtectedBlob } from "../../../services/protectedDownload";
import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type PageDto, type ListParams } from "../../../services/pagination";

export type AttachmentResource = "orders" | "trips" | "deliveries" | "occurrences";
// Additive OC110 wire contract; IDs remain opaque and no storage URL is exposed.
export interface Attachment {
  id: string;
  resource_type: AttachmentResource;
  resource_id: string;
  media_type: "image/png" | "image/jpeg";
  size_bytes: number;
  sha256: string;
  status: "ACTIVE" | "REVOKED";
  recorded_by: string;
  recorded_at: string;
  revoked_by: string | null;
  revoked_at: string | null;
}
const path = (resource: AttachmentResource, id: string) => `/attachments/${resource}/${encodeURIComponent(id)}`;
export async function listAttachments(resource: AttachmentResource, id: string, params: ListParams = {}) {
  const { data } = await api.get<PageDto<Attachment>>(path(resource, id), { params: toPageQuery(params) });
  return mapPageFromDto(data, (item) => item);
}
export async function uploadAttachment(resource: AttachmentResource, id: string, eventId: string, contentBase64: string) {
  const { data } = await api.post<Attachment>(path(resource, id), { event_id: eventId, content_base64: contentBase64 });
  return data;
}
export async function revokeAttachment(resource: AttachmentResource, id: string, attachmentId: string) {
  const { data } = await api.post<Attachment>(`${path(resource, id)}/${encodeURIComponent(attachmentId)}/revoke`, {});
  return data;
}
export async function downloadAttachment(resource: AttachmentResource, id: string, attachmentId: string) {
  return requestProtectedBlob(`${path(resource, id)}/${encodeURIComponent(attachmentId)}/content`, "Não foi possível baixar o anexo.");
}
export async function listTripAttachmentOccurrences(tripId: string) {
  const { data } = await api.get<{ id: string; type: string; description: string }[]>(`/trips/${encodeURIComponent(tripId)}/occurrences`);
  return data;
}
/**
 * Mantido como porta do módulo de anexos, mas a leitura em si é compartilhada:
 * anexos (OC110) e evidências de entrega (OC80/OC81) seguem o mesmo contrato de
 * upload, e duas cópias divergiriam na primeira mudança de limite.
 */
export function readAttachmentFile(file: File): Promise<string> {
  return readImageAsBase64(file);
}
