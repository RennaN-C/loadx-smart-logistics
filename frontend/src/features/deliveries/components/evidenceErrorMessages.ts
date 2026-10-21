import { fallbackErrorMessage } from "../../../services/apiErrorMessages";
import type { ApiError } from "../../../types/api";

/**
 * Erros do comprovante e das evidências.
 *
 * Quem usa esta tela está fechando uma entrega, muitas vezes no celular e na
 * porta do cliente. A diferença entre "não pode ainda", "já existe" e "o
 * servidor está fora" muda completamente o que a pessoa faz em seguida — e
 * nenhuma dessas três é "tente de novo".
 */
export function mapEvidenceErrorToMessage(error: ApiError): string {
  switch (error.code) {
    case "DELIVERY_RECEIPT_NOT_AVAILABLE":
      return "Esta entrega ainda não foi concluída. O comprovante nasce da conclusão, e as evidências se penduram nele.";

    case "DELIVERY_RECEIPT_HISTORY_INVALID":
      return "O histórico desta entrega está inconsistente e o comprovante não pode ser emitido. Avise a equipe com o horário.";

    case "EVIDENCE_NOT_FOUND":
      return "Esta evidência não existe mais. Atualize a lista.";

    case "EVIDENCE_REVOKED":
      return "Esta evidência foi revogada. Revogar é definitivo: para repor, registre uma nova.";

    case "EVIDENCE_IDENTITY_CONFLICT":
      // Acontece quando a MESMA chave de intenção volta com bytes diferentes.
      // Não é erro do usuário, e repetir não resolve: é preciso recomeçar o
      // envio para a chave ser gerada de novo.
      return "Este envio conflita com um registro anterior. Escolha o arquivo novamente para iniciar um novo envio.";

    case "EVIDENCE_CONTENT_INVALID":
      return "O arquivo não é uma imagem PNG ou JPEG válida, ou passa dos limites aceitos.";

    case "EVIDENCE_STORAGE_UNAVAILABLE":
      return "Não foi possível confirmar o registro no armazenamento. Consulte a lista antes de reenviar; repetir a tentativa mantém sua identificação.";

    case "DELIVERY_NOT_FOUND":
      return "Esta entrega não foi encontrada. Atualize a viagem e tente novamente.";

    case "AUTH_FORBIDDEN":
      return "Seu perfil não tem acesso a esta ação nesta entrega.";

    default:
      return fallbackErrorMessage(error);
  }
}
