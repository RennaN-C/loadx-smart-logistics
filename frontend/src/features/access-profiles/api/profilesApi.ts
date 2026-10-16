import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
export interface PermissionDefinition { code: string; module: string; label: string; delegable: boolean; classification: string }
export interface AccessProfile { id: string; name: string; description: string; active: boolean; version: number; permissions: string[]; system_role: string | null; user_count: number }
export interface ProfileInput { name: string; description: string; active: boolean; permissions: string[] }
export async function listProfiles(params: ListParams = {}) { const { data } = await api.get<PageDto<AccessProfile>>("/access-profiles", { params: toPageQuery(params) }); return mapPageFromDto(data, (item) => item); }
export async function getProfile(id: string) { const { data } = await api.get<AccessProfile>(`/access-profiles/${id}`); return data; }
export async function permissionCatalog() { const { data } = await api.get<PermissionDefinition[]>("/access-profiles/permissions"); return data; }
export async function saveProfile(input: ProfileInput, existing?: AccessProfile) { const { data } = existing ? await api.patch<AccessProfile>(`/access-profiles/${existing.id}`, { ...input, version: existing.version }) : await api.post<AccessProfile>("/access-profiles", input); return data; }
