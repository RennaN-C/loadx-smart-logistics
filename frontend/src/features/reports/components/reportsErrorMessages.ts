import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { ApiError } from "../../../types/api";

export function mapReportErrorToMessage(error: ApiError): string {
  if (error.code === "LOADING_SESSION_NOT_FOUND") {
    // Caso REAL e comum: o relatório de carregamento só existe depois que o
    // carregamento foi registrado. Sem esta frase, o usuário lê "não encontrado"
    // e vai procurar o plano, que está lá.
    return "Este plano ainda não tem carregamento registrado, então não há relatório de carregamento para gerar.";
  }

  if (error.code === "LOAD_PLAN_NOT_FOUND") {
    return "Este plano de carga não foi encontrado. Atualize a tela e tente novamente.";
  }

  if (error.code === "TRIP_NOT_FOUND") {
    return "Esta viagem não foi encontrada. Atualize a tela e tente novamente.";
  }

  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não tem permissão para baixar este relatório.";
  }

  return fallbackErrorMessage(error);
}
