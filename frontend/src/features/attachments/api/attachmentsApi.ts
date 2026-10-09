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
export function readAttachmentFile(file: File): Promise<string> {
  if (!new Set(["image/png", "image/jpeg"]).has(file.type) || file.size === 0 || file.size > 5 * 1024 * 1024) {
    return Promise.reject(new Error("Selecione PNG/JPEG de até 5 MiB."));
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Não foi possível ler o arquivo."));
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string" || !result.includes(",")) reject(new Error("Arquivo inválido."));
      else resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.readAsDataURL(file);
  });
}
