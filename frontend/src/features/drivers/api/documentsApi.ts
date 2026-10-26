import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import { documentStatuses } from "../../../components/documentStatusLabels";
export interface DocumentType { id: string; code: string; name: string }
export interface DocumentInput { document_type_id: string; reference: string; category: string | null; issued_at: string | null; expires_at: string | null }
export interface DriverDocument extends DocumentInput { id: string; driver_id: string; created_at: string; superseded_at: string | null; status: keyof typeof documentStatuses }
export interface DocumentPolicy { id: string; driver_id: string; document_type_id: string; required: boolean; allowed_categories: string[] }
export async function listDocumentTypes(): Promise<DocumentType[]> { const { data } = await api.get<DocumentType[]>("/driver-document-types"); return data; }
export async function approveDocumentType(code: string, name: string): Promise<DocumentType> { const { data } = await api.post<DocumentType>("/driver-document-types", { code, name }); return data; }
export async function listDocuments(id: string, params: ListParams = {}): Promise<Page<DriverDocument>> {
  const { data } = await api.get<PageDto<DriverDocument>>(`/drivers/${id}/documents`, { params: toPageQuery(params) }); return mapPageFromDto(data, (row) => row);
}
export async function saveDocument(id: string, input: DocumentInput, replacing?: string): Promise<DriverDocument> { const { data } = await api.post<DriverDocument>(replacing ? `/drivers/${id}/documents/${replacing}/renew` : `/drivers/${id}/documents`, input); return data; }
export async function listDocumentPolicies(id: string): Promise<DocumentPolicy[]> { const { data } = await api.get<DocumentPolicy[]>(`/drivers/${id}/document-policies`); return data; }
export async function setDocumentPolicy(id: string, typeId: string, required: boolean, allowedCategories: string[]): Promise<DocumentPolicy> { const { data } = await api.patch<DocumentPolicy>(`/drivers/${id}/document-policies/${typeId}`, { required, allowed_categories: allowedCategories }); return data; }
