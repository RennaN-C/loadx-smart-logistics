import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { ApiError } from "../../../types/api";

/**
 * Erros do carregamento e da leitura de código.
 *
 * O conferente está de pé ao lado do caminhão, com o leitor na mão. Mensagem
 * que só diz "conflito" obriga a parar e perguntar para alguém; cada caso aqui
 * diz o que aconteceu E o que fazer em seguida.
 */
export function mapLoadingErrorToMessage(error: ApiError): string {
  switch (error.code) {
    case "LOADING_PLAN_NOT_APPROVED":
      return "Este plano ainda não foi aprovado, e o carregamento só começa depois da aprovação.";

    case "LOADING_SESSION_NOT_FOUND":
      return "Esta sessão de carregamento não existe mais. Volte ao plano e abra o carregamento de novo.";

    case "LOADING_ITEM_NOT_FOUND":
      return "Nenhum volume corresponde a este código. Confira se o código é de um volume deste carregamento.";

    case "LOADING_ITEM_SESSION_MISMATCH":
      return "Este volume é de OUTRO carregamento. Nada foi conferido aqui.";

    case "LOADING_ITEM_ALREADY_CHECKED":
      return "Este volume já estava conferido. A leitura não mudou nada.";

    case "LOADING_CHECKLIST_INCOMPLETE":
      return "Ainda há volumes pendentes. O carregamento só é finalizado com o checklist inteiro conferido.";

    case "LOADING_STATUS_TRANSITION_NOT_ALLOWED":
      return "Esta ação não vale para a situação atual do carregamento. Atualize a tela e veja em que etapa ele está.";

    case "TRUCK_OPERATION_CONFLICT":
      return "O caminhão deste plano já está reservado por outra operação ativa.";

    case "AUTH_FORBIDDEN":
      // Vale a pena nomear o perfil: a tela é lida também por gestor e
      // administrador, que enxergam o checklist mas não conferem.
      return "Somente o conferente pode registrar a conferência do carregamento.";

    default:
      return fallbackErrorMessage(error);
  }
}

/**
 * O código é válido no formato que o backend exige?
 *
 * `CONFIRMADO`: prefixo literal `loadx:loading-item:` mais um UUID canônico
 * minúsculo, 55 caracteres ao todo (`docs/05`). A checagem aqui NÃO substitui a
 * do servidor — serve para o leitor de código de barras que dispara a cada
 * tecla não gastar uma requisição por caractere digitado, e para dizer "código
 * não reconhecido" sem ida e volta.
 */
const CODE_PATTERN =
  /^loadx:loading-item:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

export function isLoadingCode(value: string): boolean {
  return CODE_PATTERN.test(value.trim());
}
