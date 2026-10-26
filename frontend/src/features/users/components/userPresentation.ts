import { ApiError } from "../../../types/api";
import type { Role } from "../../auth/types";
import type { UserAccount, UserInput } from "../api/usersApi";
export const ROLE_LABELS: Record<Role, string> = { CUSTOM: "Personalizado", ADMIN: "Administrador", LOGISTICS_MANAGER: "Gestor de logística", CHECKER: "Conferente", DRIVER: "Motorista" };
const ERRORS: Record<string, string> = {
  USER_PROFILE_INVALID: "Selecione um perfil personalizado válido.",
  USER_PROFILE_INACTIVE: "O perfil selecionado está inativo ou não existe mais.",
  USER_EMAIL_ALREADY_EXISTS: "Este e-mail já está cadastrado em outra conta.",
  USER_LAST_ACTIVE_ADMIN_REQUIRED: "O último administrador ativo não pode ser desativado ou ter seu perfil alterado.",
  USER_DRIVER_NOT_FOUND: "O motorista selecionado não foi encontrado. Atualize a seleção.",
  USER_DRIVER_ALREADY_LINKED: "Este motorista já está vinculado a outra conta.",
  USER_DRIVER_ROLE_REQUIRED: "O vínculo de motorista é permitido somente para o perfil Motorista.",
  USER_NOT_FOUND: "A conta não foi encontrada. Atualize a listagem.",
  AUTH_FORBIDDEN: "Você não tem permissão para administrar usuários.",
  AUTH_INVALID_TOKEN: "Sua sessão expirou ou foi encerrada. Entre novamente.",
  VALIDATION_ERROR: "Revise os dados informados. Senhas devem ter de 15 a 128 caracteres e não podem ser comuns.",
};
export function userError(error: unknown) { return error instanceof ApiError ? ERRORS[error.code] ?? "Não foi possível concluir a operação. Tente novamente." : "Não foi possível concluir a operação. Tente novamente."; }
export function accountChanges(original: UserAccount | undefined, draft: UserInput, password: string | undefined): Partial<UserInput> {
  if (!original) return { ...draft, password };
  const changes: Partial<UserInput> = {};
  if (draft.name !== original.name) changes.name = draft.name;
  if (draft.email !== original.email) changes.email = draft.email;
  if ((draft.customProfileId ?? null) !== (original.customProfileId ?? null)) changes.customProfileId = draft.customProfileId ?? null;
  if (draft.role !== original.role) changes.role = draft.role;
  if (draft.active !== original.active) changes.active = draft.active;
  if (draft.driverId !== original.driverId) changes.driverId = draft.driverId;
  if (password !== undefined) changes.password = password;
  return changes;
}
export function revokesSessions(changes: Partial<UserInput>) { return changes.customProfileId !== undefined || changes.password !== undefined || changes.role !== undefined || changes.driverId !== undefined || changes.active === false; }

export interface PasswordDraft { enabled: boolean; password: string; confirmation: string }
export function validateDraft(draft: UserInput, security: PasswordDraft): string | null {
  if (!draft.name) return "Informe o nome da pessoa.";
  if (!security.enabled) return null;
  const length = Array.from(security.password.normalize("NFC")).length;
  if (length < 15 || length > 128) return "A senha deve ter de 15 a 128 caracteres.";
  if (security.password !== security.confirmation) return "A confirmação deve ser igual à senha informada.";
  return null;
}
