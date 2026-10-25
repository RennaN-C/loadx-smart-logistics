export function fleetSelectionKey(orderIds: readonly string[]): string {
  return [...orderIds].sort((a, b) => a.localeCompare(b)).join(",");
}

export interface FleetPreflightState {
  readonly selection: string;
  readonly status: "loading" | "ready" | "empty" | "error";
}

export function fleetReadinessHelp(mode: "single" | "automatic", hasTruck: boolean, state: FleetPreflightState | null): string | null {
  if (mode === "single") return hasTruck ? null : "Selecione um caminhão na etapa Veículos.";
  if (!state || state.status === "loading") return "Aguarde a validação da frota para os pedidos selecionados.";
  if (state.status === "error") return "Consulte a frota novamente na etapa Veículos antes de calcular.";
  if (state.status === "empty") return "Nenhum caminhão elegível. Revise a disponibilidade da frota antes de calcular.";
  return null;
}
