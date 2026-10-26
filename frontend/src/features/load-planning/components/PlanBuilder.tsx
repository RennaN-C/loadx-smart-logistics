import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import type { ListParams } from "../../../services/pagination";
import { useResourceList } from "../../../hooks/useResourceList";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import { listTruckOperationalStatus, listTrucks } from "../../trucks/api/trucksApi";
import { ApiError } from "../../../types/api";
import { createLoadPlan } from "../api/loadPlansApi";
import { useAuth } from "../../auth/hooks/useAuth";
import { FleetPreflight } from "./FleetPreflight";
import { fleetReadinessHelp, fleetSelectionKey, type FleetPreflightState } from "./fleetPreflightState";
import { useOptimizationRecovery } from "../useOptimizationRecovery";
import { OptimizationRecovery } from "./OptimizationRecovery";
import { PlanOrderSelection } from "./PlanOrderSelection";
import { DistributionFeedback } from "./DistributionFeedback";
import type { LoadDistribution, LoadPlan } from "../types";
import { mapLoadPlanErrorToMessage } from "./loadPlansErrorMessages";

interface PlanBuilderProps {
  readonly onDistributed?: (distribution: LoadDistribution) => void;
  readonly onCalculated: (plan: LoadPlan) => void;
}

const listHistoricalCustomers = (params: ListParams) => listCustomers({ ...params, archiveStatus: "all" });
/** Limite operacional do cálculo síncrono, imposto novamente pelo backend. */
const MAX_SYNC_VOLUMES = 200;
const BUILDER_STEPS = ["Pedidos", "Modalidade", "Veículos", "Revisão"] as const;

function PlanCalculateAction({ selectedCount, isCalculating, canCalculate, mode, onCalculate }: {
  readonly selectedCount: number; readonly isCalculating: boolean; readonly canCalculate: boolean;
  readonly mode: "single" | "automatic"; readonly onCalculate: () => void;
}) {
  return (
          <div className="entity-form-actions">
            <span className="plan-builder-count">
              {selectedCount} {selectedCount === 1 ? "pedido" : "pedidos"} selecionados
            </span>
            <button
              type="button"
              className="btn-primary"
              disabled={!canCalculate}
              aria-describedby="planning-calculation-help"
              aria-busy={isCalculating}
              onClick={onCalculate}
            >
              {isCalculating ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  <span>Calculando…</span>
                </>
              ) : (
                <span>{mode === "automatic" ? "Otimizar e salvar distribuição" : "Calcular plano de carga"}</span>
              )}
            </button>
          </div>
  );
}

export function PlanBuilder({ onCalculated, onDistributed }: PlanBuilderProps) {
  const { items: trucks, status: trucksStatus, refetch: reloadTrucks } = useResourceList(listTrucks);
  // Duas consultas porque os dois contratos são diferentes: `GET /trucks` traz as
  // medidas internas, que são o que ajuda a escolher o baú; `operational-status`
  // traz a disponibilidade da OC67, e não traz medida nenhuma.
  const { items: situacoes, status: situationsStatus, refetch: reloadSituations } = useResourceList(listTruckOperationalStatus);
  const { items: orders, status: ordersStatus, refetch: reloadOrders } = useResourceList(listOrders);
  const { items: customers } = useResourceList(listHistoricalCustomers);

  const { user } = useAuth();
  const recovery = useOptimizationRecovery(user?.id ?? "", onDistributed);
  const [mode, setMode] = useState<"single" | "automatic">("single");
  const [fleetPreflight, setFleetPreflight] = useState<FleetPreflightState | null>(null);
  const requestPending = useRef(false);
  const [distributionError, setDistributionError] = useState<unknown>(null);
  const [truckId, setTruckId] = useState("");
  const [selectedOrders, setSelectedOrders] = useState<string[]>([]);
  const [isCalculating, setIsCalculating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const stepsRef = useRef<HTMLElement>(null);
  function selectStep(index: number) {
    setStep(index);
    requestAnimationFrame(() => stepsRef.current?.querySelector<HTMLButtonElement>('[aria-current="step"]')?.focus());
  }

  // Só caminhão ativo carrega, e só pedido READY entra em plano (regra do backend).
  const activeTrucks = useMemo(() => trucks.filter((truck) => truck.active && !situacoes.some((status) => status.id === truck.id && (status.hasMaintenanceConflict || status.hasDocumentConflict))), [trucks, situacoes]);
  /**
   * Quais caminhões já estão comprometidos, segundo a OC67.
   *
   * O conflito NÃO é calculado aqui: vem pronto de `operational-status`. Caminhão
   * cuja situação ainda não chegou fica de fora do mapa e aparece sem aviso —
   * deixar de oferecê-lo seria esconder opção que o backend aceita.
   */
  const emOperacao = useMemo(
    () => new Set(situacoes.filter((item) => item.hasOperationConflict).map((item) => item.id)),
    [situacoes],
  );
  const readyOrders = useMemo(() => orders.filter((order) => order.status === "READY"), [orders]);
  const customerNames = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer.name])),
    [customers],
  );
  // Uma linha do pedido pode representar centenas de volumes físicos.
  const selectedReadyOrders = readyOrders.filter((order) => selectedOrders.includes(order.id));
  const selectedVolumeCount = selectedReadyOrders.reduce((sum, order) => sum + (order.volumeCount ?? 0), 0);
  const hasUnknownVolumeCounts = selectedReadyOrders.some((order) => order.volumeCount === undefined);
  const exceedsVolumeLimit = selectedVolumeCount > MAX_SYNC_VOLUMES;

  function toggleOrder(orderId: string) {
    setFleetPreflight(null);
    setSelectedOrders((current) =>
      current.includes(orderId) ? current.filter((id) => id !== orderId) : [...current, orderId],
    );
  }

  async function handleCalculate() {
    if (requestPending.current || !canCalculate) return;
    requestPending.current = true;
    setErrorMessage(null);
    setDistributionError(null);
    setIsCalculating(true);

    try {
      if (mode === "automatic") {
        await recovery.start(selectedOrders);
      } else {
        onCalculated(await createLoadPlan({ truckId, orderIds: selectedOrders }));
      }
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      if (mode === "automatic") setDistributionError(apiError);
      else setErrorMessage(mapLoadPlanErrorToMessage(apiError));
    } finally {
      requestPending.current = false;
      setIsCalculating(false);
    }
  }

  const isLoading = ordersStatus === "loading" || (mode === "single" && (trucksStatus === "loading" || situationsStatus === "loading"));
  const hasListError = ordersStatus === "error" || (mode === "single" && (trucksStatus === "error" || situationsStatus === "error"));
  const orderSelectionHelp = selectedOrders.length === 0 ? "Selecione pelo menos um pedido na etapa Pedidos."
    : selectedReadyOrders.length !== selectedOrders.length ? "Há pedidos que não estão mais prontos. Revise a seleção na etapa Pedidos."
      : exceedsVolumeLimit ? `A seleção ultrapassa ${MAX_SYNC_VOLUMES} volumes. Reduza as quantidades na etapa Pedidos.` : null;
  const currentFleet = fleetPreflight?.selection === fleetSelectionKey(selectedOrders) ? fleetPreflight : null;
  const fleetHelp = fleetReadinessHelp(mode, activeTrucks.some((truck) => truck.id === truckId), currentFleet);
  const calculationHelp = isCalculating || recovery.working ? "Aguarde a conclusão do cálculo."
    : isLoading ? "Aguarde o carregamento dos dados do planejamento."
      : hasListError ? "Recarregue os dados do planejamento antes de continuar."
        : orderSelectionHelp ?? fleetHelp;
  const canCalculate = !calculationHelp && !recovery.request;
  const nextHelp = step === 0 ? orderSelectionHelp : step === 2 ? calculationHelp : null;

  function changeMode(value: "single" | "automatic") {
    setFleetPreflight(null);
    setMode(value);
  }

  if (recovery.request) return <div className="plan-builder">
    <DistributionFeedback error={recovery.error} />
    <OptimizationRecovery count={recovery.request.orderIds.length} working={recovery.working}
      canDiscard={recovery.canDiscard} onDiscard={recovery.discard}
      onConsult={() => void recovery.consult()} onRetry={() => void recovery.retry()} />
  </div>;

  return (
    <div className="plan-builder">
      <nav ref={stepsRef} aria-label="Etapas do planejamento" className="planning-steps"><ol>{BUILDER_STEPS.map((title, index) => <li key={title}>
        <button type="button" aria-current={step === index ? "step" : undefined} disabled={isCalculating} onClick={() => selectStep(index)}>
          <span aria-hidden="true">{index + 1}</span>{title}
        </button>
      </li>)}</ol></nav>
      {onDistributed ? <fieldset className="distribution-mode" disabled={isCalculating} hidden={step !== 1}>
        <legend>Como planejar esta carga?</legend>
        <label htmlFor="planning-single"><input id="planning-single" aria-label="Um caminhão" type="radio" name="planning-mode" checked={mode === "single"} onChange={() => changeMode("single")} /><span><strong>Um caminhão</strong><small>Escolha o veículo e calcule a carga.</small></span></label>
        <label htmlFor="planning-automatic"><input id="planning-automatic" aria-label="Seleção automática da frota" type="radio" name="planning-mode" checked={mode === "automatic"} onChange={() => changeMode("automatic")} /><span><strong>Seleção automática da frota · multi-caminhões</strong><small>Distribua os volumes entre veículos elegíveis e revise a proposta antes de aprovar.</small></span></label>
      </fieldset> : null}
      {!onDistributed && step === 1 ? <p className="entity-form-help">Escolha um caminhão para calcular o plano de carga.</p> : null}
      <DistributionFeedback error={recovery.error ?? distributionError} />
      {distributionError ? <p className="entity-form-help">Se a conexão caiu após o envio, consulte <Link to="/planning">Planos existentes</Link> antes de repetir: a proposta pode ter sido salva.</p> : null}
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      {isLoading ? (
        <output className="plan-builder-loading" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          <span>
            <strong>Carregando caminhões e pedidos…</strong>
            <span className="plan-builder-loading-message">Consultando os dados e a disponibilidade operacional para montar o plano.</span>
          </span>
        </output>
      ) : null}

      {!isLoading && hasListError ? (
        <div className="plan-builder-feedback">
          <AlertBanner>Não foi possível carregar os dados necessários para planejar. Nenhuma carga foi alterada.</AlertBanner>
          <button type="button" className="btn-secondary" onClick={() => {
            void Promise.all([reloadTrucks(), reloadOrders(), reloadSituations()]);
          }}>Tentar novamente</button>
        </div>
      ) : null}

      {!isLoading && !hasListError ? (
        <>
          <div hidden={step !== 2} className="planning-step-content">
          <h3>Selecione o veículo</h3>
          {mode === "single" ? <div className="entity-form-row">
            <FormField
              id="plan-truck"
              label="CAMINHÃO"
              hint="Só caminhões ativos aparecem aqui. Os marcados como em operação já estão comprometidos com outra operação — ainda dá para planejar, mas vale conferir antes."
            >
              <select id="plan-truck" value={truckId} onChange={(event) => setTruckId(event.target.value)}>
                <option value="">Selecione o caminhão</option>
                {activeTrucks.map((truck) => (
                  <option key={truck.id} value={truck.id}>
                    {truck.plate} — {truck.model} ({truck.internalLengthCm}×{truck.internalWidthCm}×
                    {truck.internalHeightCm} cm)
                    {emOperacao.has(truck.id) ? " — em operação" : ""}
                  </option>
                ))}
              </select>
            </FormField>
          </div> : <><p className="entity-form-help">A otimização pode usar de 1 a 10 caminhões. Só será salva uma proposta que comporte todos os volumes, até o limite de 200. Disponibilidade não significa reserva da frota.</p>{selectedOrders.length > 0 && !orderSelectionHelp ? <FleetPreflight orderIds={selectedOrders} onStateChange={setFleetPreflight} /> : null}</>}
          </div>

          <div hidden={step !== 0} className="planning-step-content">
          <h3>Selecione os pedidos</h3>
          <PlanOrderSelection readyOrders={readyOrders} selectedOrders={selectedOrders} customerNames={customerNames}
            isCalculating={isCalculating} selectedVolumeCount={selectedVolumeCount} hasUnknownVolumeCounts={hasUnknownVolumeCounts}
            exceedsVolumeLimit={exceedsVolumeLimit} maxVolumes={MAX_SYNC_VOLUMES} onToggle={toggleOrder} />
          </div>
          <div hidden={step !== 3} className="planning-step-content">
          <h3>Revise antes de calcular</h3>
          <dl className="planning-review">
            <div><dt>Pedidos selecionados</dt><dd>{selectedOrders.length}</dd></div>
            <div><dt>Volumes físicos</dt><dd>{selectedVolumeCount}{hasUnknownVolumeCounts ? " · quantidades parciais" : ""}</dd></div>
            <div><dt>Modalidade</dt><dd>{mode === "automatic" ? "Seleção automática da frota" : "Um caminhão"}</dd></div>
            <div><dt>Veículo</dt><dd>{mode === "automatic" ? "Definido pelo otimizador" : activeTrucks.find((truck) => truck.id === truckId)?.plate ?? "Não selecionado"}</dd></div>
          </dl>
          <p className="entity-form-help">O cálculo salva o planejamento. A aprovação e o início da operação continuam sendo ações separadas.</p>
          <aside className="planning-ai-precalculation" aria-label="Etapa de IA">
            <strong>Explicação por IA — etapa separada e opcional</strong>
            <p>Primeiro o sistema calcula e valida as posições dos volumes pelas regras físicas. Depois, no resultado salvo, você pode solicitar uma explicação por IA sobre o aproveitamento e as decisões do plano. A IA não altera a distribuição, os pesos ou a segurança do carregamento.</p>
          </aside>
          <p id="planning-calculation-help" className="entity-form-help" role={exceedsVolumeLimit ? "alert" : "status"}>{exceedsVolumeLimit ? <>Desmarque pedidos para ficar dentro do limite de {MAX_SYNC_VOLUMES} volumes. Revise a seleção na etapa Pedidos ou ajuste as quantidades em <Link to="/orders">Pedidos</Link>.</> : calculationHelp ?? "Tudo pronto. O cálculo salvará o planejamento para revisão e aprovação."}</p>
          <PlanCalculateAction selectedCount={selectedOrders.length} isCalculating={isCalculating}
            canCalculate={canCalculate} mode={mode} onCalculate={() => void handleCalculate()} />
          </div>
        </>
      ) : null}
      <div className="planning-step-actions">
        {step > 0 ? <button type="button" className="btn-secondary" disabled={isCalculating} onClick={() => selectStep(step - 1)}>Voltar</button> : <span />}
        {step < BUILDER_STEPS.length - 1 ? <button type="button" className="btn-primary" aria-describedby="planning-step-help" disabled={isCalculating || isLoading || hasListError || Boolean(nextHelp)} onClick={() => selectStep(step + 1)}>Continuar</button> : null}
      </div>
      {step < BUILDER_STEPS.length - 1 ? <p id="planning-step-help" className="entity-form-help" aria-live="polite">{isLoading ? "Aguarde o carregamento dos dados do planejamento." : hasListError ? "Recarregue os dados do planejamento antes de continuar." : nextHelp}</p> : null}
    </div>
  );
}
