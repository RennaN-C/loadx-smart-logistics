import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { FieldLabels } from "../../../services/validationErrors";
import type { ApiError } from "../../../types/api";

/** Nome do campo no backend -> rótulo da tela, para o 422 dizer QUAL campo. */
const LOGIN_FIELDS: FieldLabels = {
  email: "E-mail",
  password: "Senha",
};

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

  return fallbackErrorMessage(error, LOGIN_FIELDS);
}
