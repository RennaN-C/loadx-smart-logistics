import type { ApiError } from "../../../types/api";

export function mapLoginErrorToMessage(error: ApiError): string {
  if (error.code === "AUTH_INVALID_CREDENTIALS") {
    return "E-mail ou senha inválidos. Verifique e tente novamente.";
  }

  if (error.code === "AUTH_USER_INACTIVE") {
    return "Este usuário está inativo. Fale com o administrador do sistema.";
  }

  if (error.code === "AUTH_RATE_LIMITED") {
    return "Muitas tentativas de login. Aguarde e tente novamente.";
  }

  return error.message;
}
