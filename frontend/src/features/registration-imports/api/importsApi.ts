import { api } from "../../../services/api";
import { requestProtectedBlob } from "../../../services/protectedDownload";
import { mapPageFromDto, toPageQuery, type PageDto, type ListParams } from "../../../services/pagination";

export type ImportEntity = "customers" | "products" | "trucks" | "drivers";
export interface ImportFile { file_name: string; content_base64: string }
export interface ImportRowError { line: number; field: string; code: string; message: string }
export interface ImportPreview {
  entity_type: ImportEntity; sha256: string; row_count: number; valid_count: number;
  can_confirm: boolean; errors: ImportRowError[]; rows: { line: number; data: Record<string, unknown> }[];
}
export interface ImportSummary {
  id: string; entity_type: ImportEntity; recorded_by: string; recorded_at: string;
  sha256: string; status: "COMPLETED" | "REJECTED"; row_count: number; created_count: number; rejected_count: number;
}
export interface ImportResult extends ImportSummary { errors: ImportRowError[]; records: { line: number; id: string }[] }
const prefix = "/registration-imports";
export async function previewImport(entity: ImportEntity, file: ImportFile) {
  const { data } = await api.post<ImportPreview>(`${prefix}/${entity}/preview`, file);
  return data;
}
export async function confirmImport(entity: ImportEntity, file: ImportFile, previewSha: string, eventId: string) {
  const { data } = await api.post<ImportResult>(`${prefix}/${entity}/confirm`, { ...file, preview_sha256: previewSha, event_id: eventId });
  return data;
}
export async function listImports(entity: ImportEntity, params: ListParams = {}) {
  const { data } = await api.get<PageDto<ImportSummary>>(prefix, { params: { ...toPageQuery(params), entity_type: entity } });
  return mapPageFromDto(data, (item) => item);
}
export async function getImport(id: string) {
  const { data } = await api.get<ImportResult>(`${prefix}/${encodeURIComponent(id)}`);
  return data;
}
export function downloadImportTemplate(entity: ImportEntity) {
  return requestProtectedBlob(`${prefix}/${entity}/template`, "Não foi possível baixar o modelo CSV.");
}
export function readCsvFile(file: File): Promise<ImportFile> {
  if (!file.name.toLowerCase().endsWith(".csv") || file.size === 0 || file.size > 1024 * 1024) {
    return Promise.reject(new Error("Selecione um CSV UTF-8 de até 1 MiB, com ao menos um registro."));
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Não foi possível ler o CSV."));
    reader.onload = () => {
      const value = reader.result;
      if (typeof value !== "string" || !value.includes(",")) reject(new Error("Arquivo inválido."));
      else resolve({ file_name: file.name, content_base64: value.slice(value.indexOf(",") + 1) });
    };
    reader.readAsDataURL(file);
  });
}
