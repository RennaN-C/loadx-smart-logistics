import type { ApiError } from "../types/api";
import { validationMessage, type FieldLabels } from "./validationErrors";

/**
 * Último degrau de tradução de erro, comum a todas as features.
 *
 * A ordem importa: primeiro o 422 detalhado, que nomeia o campo; depois os
 * códigos que não pertencem a nenhum domínio (rede, sessão, permissão); por
 * último o texto que o backend mandou, que já vem em português.
 *
 * Cada feature continua dona dos códigos DELA — quem sabe explicar
 * `TRUCK_PLATE_ALREADY_EXISTS` é a tela de caminhões, não este arquivo.
 */
const SHARED_MESSAGES: Readonly<Record<string, string>> = {
  NETWORK_ERROR:
    "Não foi possível falar com o servidor. Verifique sua conexão e tente de novo.",
  UNKNOWN_ERROR:
    "Ocorreu um erro inesperado. Tente de novo; se continuar, avise a equipe com o horário.",
  AUTH_FORBIDDEN: "Seu perfil não tem permissão para esta ação.",
  AUTH_INVALID_TOKEN: "Sua sessão expirou. Entre novamente para continuar.",
  AUTH_USER_INACTIVE: "Este usuário está inativo. Fale com o administrador do sistema.",
  AUTH_ORIGIN_FORBIDDEN:
    "O servidor recusou a requisição por causa do endereço de origem. Acesse o sistema pelo endereço oficial.",
  AUTH_RATE_LIMITED: "Muitas tentativas seguidas. Aguarde um pouco e tente de novo.",
  RATE_LIMITED: "Muitas requisições seguidas. Aguarde um pouco e tente de novo.",
  SERVICE_UNAVAILABLE: "O servidor está indisponível no momento. Tente de novo em instantes.",
};

export function fallbackErrorMessage(error: ApiError, labels: FieldLabels = {}): string {
  return validationMessage(error, labels) ?? SHARED_MESSAGES[error.code] ?? error.message;
}
