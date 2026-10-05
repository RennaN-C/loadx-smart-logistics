import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { ApiError } from "../../../types/api";

/**
 * Erros do painel operacional (OC74).
 *
 * `GET /operational-indicators` não recebe id na rota, então um 404 aqui nunca
 * significa "este indicador não existe": significa que a ROTA não existe no
 * servidor que respondeu. Sem este desvio o caso cai em `UNKNOWN_ERROR` e a
 * tela diz "erro inesperado", que manda a pessoa procurar defeito no lugar
 * errado — foi exatamente o que aconteceu no ambiente local enquanto a API da
 * OC69 ainda não estava publicada.
 */
export function mapOperationalIndicatorsError(error: ApiError): string {
  if (error.status === 404) {
    return "Este ambiente ainda não publica a API de indicadores. Quando o servidor for atualizado, o painel carrega sozinho.";
  }

  return fallbackErrorMessage(error);
}
