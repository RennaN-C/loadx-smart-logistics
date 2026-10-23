import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { mapLoadPlanErrorToMessage } from "./loadPlansErrorMessages";

const MESSAGES: Readonly<Record<string, string>> = {
  OPTIMIZATION_IN_PROGRESS: "Esta otimização ainda está em andamento. Aguarde e consulte o resultado; não inicie outra solicitação.",
  OPTIMIZATION_NOT_FOUND: "Ainda não há resultado confirmado para esta solicitação. Você pode consultar novamente ou repetir a mesma solicitação com segurança.",
  IDEMPOTENCY_PAYLOAD_MISMATCH: "A identidade desta solicitação pertence a outra seleção de pedidos. Consulte o resultado original antes de continuar.",
  DISTRIBUTION_CAPACITY_INSUFFICIENT: "A frota elegível não comportou toda a carga na busca realizada. Nenhuma proposta parcial foi salva. Revise os pedidos ou a disponibilidade da frota.",
  DISTRIBUTION_CAPACITY_REJECTED: "Há volumes que não couberam no veículo. Nenhuma alteração parcial foi salva.",
  DISTRIBUTION_VERSION_CONFLICT: "Esta parte foi atualizada em outra operação. Atualize a distribuição antes de tentar novamente.",
  DISTRIBUTION_ORDER_CLAIMED: "Um pedido já pertence a outra distribuição ativa. Consulte os planos existentes.",
  DISTRIBUTION_NOT_FOUND: "Esta distribuição não foi encontrada.",
  DISTRIBUTION_PART_NOT_FOUND: "Esta parte não foi encontrada. Atualize a distribuição.",
  DISTRIBUTION_INCOMPLETE: "A distribuição está incompleta. Reprocesse as partes canceladas antes de aprovar.",
  DISTRIBUTION_IMMUTABLE: "A situação atual da distribuição não permite alterações.",
  DISTRIBUTION_TRUCK_DUPLICATED: "Este caminhão já pertence a outra parte da distribuição.",
  DISTRIBUTION_INTEGRITY_CONFLICT: "Houve um conflito com outra operação. Atualize os dados antes de continuar.",
  TRUCK_OPERATION_CONFLICT: "O caminhão está comprometido com outra operação. Atualize a disponibilidade ou escolha outro.",
  TRUCK_IN_MAINTENANCE: "O caminhão está em manutenção e não pode receber esta carga.",
  TRUCK_DOCUMENT_INELIGIBLE: "O caminhão possui uma pendência documental que impede esta operação.",
};
function isUnconfirmedOutcome(error: unknown): boolean {
  return error instanceof ApiError && error.status === undefined
    && (error.code === "NETWORK_ERROR" || error.code === "UNKNOWN_ERROR");
}

function distributionErrorMessage(error: unknown): string {
  if (isUnconfirmedOutcome(error)) {
    return "A conexão foi interrompida e não foi possível confirmar o resultado. A distribuição pode ter sido salva no servidor. Consulte Planos existentes antes de repetir a otimização.";
  }
  if (!(error instanceof ApiError)) return "Não foi possível concluir a solicitação. Tente novamente.";
  return MESSAGES[error.code] ?? mapLoadPlanErrorToMessage(error);
}
export function DistributionFeedback({ error }: { readonly error: unknown }) {
  if (!error) return null;
  return <AlertBanner>
    <strong>{distributionErrorMessage(error)}</strong>
    {isUnconfirmedOutcome(error) ? <p><a href="/planning">Conferir Planos existentes antes de tentar novamente</a></p> : null}
    {error instanceof ApiError ? <details className="distribution-error-detail"><summary>Detalhes da resposta</summary>
      <p>{error.message} ({error.code})</p>
      {/* React escapes API text. Preserve structured diagnostics without interpreting them as success. */}
      {error.details.length > 0 ? <pre>{JSON.stringify(error.details, null, 2)}</pre> : null}
    </details> : null}
  </AlertBanner>;
}
