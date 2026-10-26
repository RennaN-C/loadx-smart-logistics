import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { mapLoadPlanErrorToMessage } from "./loadPlansErrorMessages";

const MESSAGES: Readonly<Record<string, string>> = {
  OPTIMIZATION_IN_PROGRESS: "Esta otimização ainda está em andamento. Aguarde e consulte o resultado; não inicie outra solicitação.",
  OPTIMIZATION_NOT_FOUND: "Nenhum resultado foi encontrado para esta tentativa. Consulte novamente; se o servidor confirmar a ausência, você poderá encerrar a tentativa e iniciar outro planejamento.",
  IDEMPOTENCY_PAYLOAD_MISMATCH: "A identidade desta solicitação pertence a outra seleção de pedidos. Consulte o resultado original antes de continuar.",
  DISTRIBUTION_CAPACITY_INSUFFICIENT: "Não foi possível distribuir todos os volumes com os caminhões disponíveis. Nenhum planejamento parcial foi salvo.",
  DISTRIBUTION_CAPACITY_REJECTED: "Há volumes que não couberam no veículo. Nenhuma alteração parcial foi salva.",
  DISTRIBUTION_VERSION_CONFLICT: "Esta parte foi atualizada em outra operação. Atualize a distribuição antes de tentar novamente.",
  DISTRIBUTION_ORDER_CLAIMED: "Um pedido já pertence a outra distribuição ativa. Consulte os planos existentes.",
  DISTRIBUTION_NOT_FOUND: "Esta distribuição não foi encontrada.",
  DISTRIBUTION_PART_NOT_FOUND: "Esta parte não foi encontrada. Atualize a distribuição.",
  DISTRIBUTION_INCOMPLETE: "A distribuição está incompleta. Reprocesse as partes canceladas antes de aprovar.",
  DISTRIBUTION_IMMUTABLE: "Esta distribuição já foi concluída ou cancelada e não pode mais ser alterada. Consulte o histórico ou crie uma nova proposta.",
  DISTRIBUTION_TRUCK_DUPLICATED: "Este caminhão já pertence a outra parte da distribuição.",
  DISTRIBUTION_INTEGRITY_CONFLICT: "Houve um conflito com outra operação. Atualize os dados antes de continuar.",
  TRUCK_OPERATION_CONFLICT: "O caminhão está comprometido com outra operação. Atualize a disponibilidade ou escolha outro.",
  TRUCK_IN_MAINTENANCE: "O caminhão está em manutenção e não pode receber esta carga.",
  TRUCK_DOCUMENT_INELIGIBLE: "O caminhão possui uma pendência documental que impede esta operação.",
};
function isUnconfirmedOutcome(error: unknown): boolean {
  return error instanceof ApiError && (error.status === undefined || error.status === 408 || error.status >= 500)
    && (error.code === "NETWORK_ERROR" || error.code === "UNKNOWN_ERROR");
}

function distributionErrorMessage(error: unknown): string {
  if (isUnconfirmedOutcome(error)) {
    return "Não foi possível confirmar o resultado. A distribuição pode ter sido salva no servidor. Consulte o estado salvo antes de repetir a operação.";
  }
  if (!(error instanceof ApiError)) return "Não foi possível concluir a solicitação. Tente novamente.";
  return MESSAGES[error.code] ?? mapLoadPlanErrorToMessage(error);
}
/** Somente diagnósticos operacionais seguros chegam à interface. */
const REASON_HINTS: Readonly<Record<string, string>> = {
  COLLISION: "Não foi encontrada posição livre sem sobrepor volumes.",
  TRUCK_DIMENSIONS_EXCEEDED: "As dimensões de alguns volumes não cabem no espaço disponível.",
  TRUCK_WEIGHT_EXCEEDED: "O peso excederia a capacidade de pelo menos um caminhão.",
  NON_STACKABLE_SUPPORT: "Há itens que não permitem empilhamento.",
  FRAGILE_SUPPORT_WEIGHT_EXCEEDED: "O empilhamento comprometeria a proteção de itens frágeis.",
  INSUFFICIENT_SUPPORT: "Não foi encontrada uma superfície de apoio segura.",
  NO_VALID_POSITION: "Não foi encontrada uma posição segura para alguns volumes.",
};

function capacityDiagnostics(error: ApiError): { remaining: number; hints: string[]; unavailableTrucks: number } | null {
  const detail = error.details.find(
    (entry): entry is Record<string, unknown> =>
      typeof entry === "object" && entry !== null && "remaining_volumes" in entry,
  );
  if (!detail || !Array.isArray(detail.remaining_volumes)) return null;
  const hints = new Set<string>();
  for (const volume of detail.remaining_volumes) {
    if (typeof volume !== "object" || volume === null || !("reasons" in volume) || !Array.isArray(volume.reasons)) continue;
    for (const reason of volume.reasons) {
      if (typeof reason === "string" && REASON_HINTS[reason]) hints.add(REASON_HINTS[reason]);
    }
  }
  return {
    remaining: detail.remaining_volumes.length,
    hints: Array.from(hints).slice(0, 3),
    unavailableTrucks: Array.isArray(detail.ineligible_trucks) ? detail.ineligible_trucks.length : 0,
  };
}

export function DistributionFeedback({ error }: { readonly error: unknown }) {
  if (!error) return null;
  return <AlertBanner>
    <strong>{distributionErrorMessage(error)}</strong>
    {isUnconfirmedOutcome(error) ? <p><a href="/planning">Conferir Planos existentes antes de tentar novamente</a></p> : null}
    {error instanceof ApiError && error.code === "DISTRIBUTION_CAPACITY_INSUFFICIENT" ? (() => {
      const diagnostic = capacityDiagnostics(error);
      return <div className="distribution-feedback-guidance">
        {diagnostic?.remaining ? <p>{diagnostic.remaining} {diagnostic.remaining === 1 ? "volume ficou" : "volumes ficaram"} sem posição segura nesta tentativa.</p> : null}
        {diagnostic?.hints.length ? <p><strong>Possíveis impedimentos:</strong> {diagnostic.hints.join(" ")}</p> : null}
        {diagnostic?.unavailableTrucks ? <p>{diagnostic.unavailableTrucks} {diagnostic.unavailableTrucks === 1 ? "caminhão não estava elegível" : "caminhões não estavam elegíveis"} para participar do cálculo.</p> : null}
        <p><strong>Como resolver:</strong> confira dimensões, peso, fragilidade e quantidade dos volumes; verifique quais caminhões estão disponíveis e tente novamente com uma seleção adequada.</p>
      </div>;
    })() : null}
  </AlertBanner>;
}
