import type { StatusTone } from "../../../components/StatusPill";
import type { TruckOperationalStatus } from "../types";

/**
 * Como a situação de um caminhão aparece na tela.
 *
 * `RISCO IDENTIFICADO` evitado aqui: `available` **não é recalculado**. Ele
 * chega pronto do backend, onde a regra mora (`fleet/service.py`, OC64/OC67).
 * Refazer a conta no frontend criaria uma segunda fonte de verdade que
 * divergiria no dia em que a regra mudasse.
 *
 * `active` e `hasOperationConflict` entram só para EXPLICAR a indisponibilidade.
 * Os dois podem ser verdade ao mesmo tempo — caminhão arquivado que ainda está
 * numa operação —, e nesse caso os dois motivos aparecem.
 */
export interface FleetStatusView {
  readonly tone: StatusTone;
  readonly label: string;
  /** Por que não está disponível. `null` quando está. */
  readonly reason: string | null;
}

export function describeFleetStatus(truck: TruckOperationalStatus): FleetStatusView {
  if (truck.available) {
    return { tone: "good", label: "Disponível", reason: null };
  }

  const motivos: string[] = [];
  if (!truck.active) motivos.push("cadastro arquivado");
  if (truck.hasOperationConflict) motivos.push("já está em operação");

  return {
    // Em operação é situação normal e passageira; cadastro arquivado é decisão de
    // quem administra. Tons diferentes porque exigem ações diferentes.
    tone: truck.active ? "warn" : "neutral",
    label: "Indisponível",
    // Sem motivo conhecido quando o backend recusa por regra que esta tela não
    // conhece. Dizer "indisponível" e parar é mais honesto que inventar causa.
    reason: motivos.length === 0 ? null : capitalize(motivos.join(" e ")),
  };
}

function capitalize(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}
