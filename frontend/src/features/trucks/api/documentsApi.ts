import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";

// DTOs retain the public snake_case contract; this feature needs no second mapping.
export type DocumentKind = "CRLV" | "LICENSING" | "INSURANCE";
export type DocumentStatus = "VALID" | "EXPIRING" | "EXPIRED" | "NOT_YET_VALID" | "SUPERSEDED";
export interface DocumentInput {
  kind: DocumentKind;
  reference: string;
  issued_at: string | null;
  expires_at: string | null;
  file_reference: string | null;
}
export interface TruckDocument extends DocumentInput {
  id: string;
  truck_id: string;
  created_at: string;
  superseded_at: string | null;
  status: DocumentStatus;
}
export interface DocumentPolicy { id: string; truck_id: string; kind: DocumentKind; required: boolean }
export async function listDocuments(truckId: string, params: ListParams = {}): Promise<Page<TruckDocument>> {
  const { data } = await api.get<PageDto<TruckDocument>>(`/trucks/${truckId}/documents`, { params: toPageQuery(params) });
  return mapPageFromDto(data, (row) => row);
}
export async function saveDocument(truckId: string, input: DocumentInput, replacing?: string): Promise<TruckDocument> {
  const path = replacing ? `/trucks/${truckId}/documents/${replacing}/renew` : `/trucks/${truckId}/documents`;
  const { data } = await api.post<TruckDocument>(path, input);
  return data;
}
export async function listDocumentPolicies(truckId: string): Promise<DocumentPolicy[]> {
  const { data } = await api.get<DocumentPolicy[]>(`/trucks/${truckId}/document-policies`);
  return data;
}
export async function setDocumentPolicy(truckId: string, kind: DocumentKind, required: boolean): Promise<DocumentPolicy> {
  const { data } = await api.patch<DocumentPolicy>(`/trucks/${truckId}/document-policies/${kind}`, { required });
  return data;
}
