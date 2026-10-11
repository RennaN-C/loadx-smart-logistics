import { ApiError } from "../../../types/api";
import { validationMessage } from "../../../services/validationErrors";
const LABELS = { name: "Nome", email: "E-mail", current_password: "Senha atual", new_password: "Nova senha" };
export function accountError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Não foi possível concluir a operação. Tente novamente.";
  if (error.code === "AUTH_CURRENT_PASSWORD_INVALID") return "Senha atual incorreta.";
  if (error.code === "USER_EMAIL_ALREADY_EXISTS") return "E-mail já cadastrado. Informe outro endereço.";
  if (error.code === "AUTH_RATE_LIMITED") return "Muitas tentativas. Aguarde antes de tentar novamente.";
  if (error.code === "AUTH_INVALID_TOKEN" || error.code === "AUTH_USER_INACTIVE") return "Sua sessão expirou ou foi encerrada. Entre novamente.";
  return validationMessage(error, LABELS) ?? "Não foi possível concluir a operação. Tente novamente.";
}
