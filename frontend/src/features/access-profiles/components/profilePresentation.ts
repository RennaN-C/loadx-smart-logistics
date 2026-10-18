import type { PermissionDefinition } from "../api/profilesApi";
import { ApiError } from "../../../types/api";
const MESSAGES: Record<string, string> = { PROFILE_VERSION_CONFLICT: "Este perfil foi alterado por outra pessoa. Feche e reabra o formulário.", PROFILE_IN_USE: "Remova os usuários associados antes de desativar o perfil.", PROFILE_CONFLICT: "Já existe um perfil com este nome ou a associação é inválida.", PROFILE_NAME_RESERVED: "Este nome identifica um perfil protegido do sistema.", PROFILE_NOT_FOUND: "Perfil não encontrado. Atualize a listagem.", VALIDATION_ERROR: "Revise o nome e as permissões. Somente permissões delegáveis são aceitas." };
export function profileError(error: unknown): string { return error instanceof ApiError ? MESSAGES[error.code] ?? "Não foi possível salvar o perfil. Tente novamente." : "Não foi possível salvar o perfil. Tente novamente."; }

export const MODULE_LABELS: Record<string, string> = { customers: "Clientes", products: "Produtos", trucks: "Caminhões", drivers: "Motoristas", orders: "Pedidos", planning: "Planejamento", loading: "Carregamento", trips: "Viagens", deliveries: "Entregas", occurrences: "Ocorrências", reports: "Relatórios", messages: "Comunicação", audit: "Auditoria", users: "Usuários", profiles: "Perfis de acesso", settings: "Configurações", integrations: "Integrações", imports: "Importações" };

export function permissionGroups(catalog: PermissionDefinition[]) {
  const groups = new Map<string, PermissionDefinition[]>();
  for (const item of catalog) groups.set(item.module, [...(groups.get(item.module) ?? []), item]);
  return [...groups];
}
