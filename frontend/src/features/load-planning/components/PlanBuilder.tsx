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
  const requestPending = useRef(false);
  const [distributionError, setDistributionError] = useState<unknown>(null);
  const [truckId, setTruckId] = useState("");
  const [selectedOrders, setSelectedOrders] = useState<string[]>([]);
  const [isCalculating, setIsCalculating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
    setSelectedOrders((current) =>
      current.includes(orderId) ? current.filter((id) => id !== orderId) : [...current, orderId],
    );
  }

  async function handleCalculate() {
    if (requestPending.current) return;
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
  const canCalculate = (mode === "automatic" || activeTrucks.some((truck) => truck.id === truckId))
    && selectedOrders.length > 0 && !exceedsVolumeLimit && !isCalculating && !recovery.request && !recovery.working;

  return (
    <div className="plan-builder">
      {onDistributed ? <fieldset className="distribution-mode" disabled={isCalculating}>
        <legend>Como planejar esta carga?</legend>
        <label htmlFor="planning-single"><input id="planning-single" aria-label="Um caminhão" type="radio" name="planning-mode" checked={mode === "single"} onChange={() => setMode("single")} /><span><strong>Um caminhão</strong><small>Escolha o veículo e calcule a carga.</small></span></label>
        <label htmlFor="planning-automatic"><input id="planning-automatic" aria-label="Seleção automática da frota" type="radio" name="planning-mode" checked={mode === "automatic"} onChange={() => setMode("automatic")} /><span><strong>Seleção automática da frota</strong><small>O servidor seleciona os veículos elegíveis e salva uma proposta completa.</small></span></label>
      </fieldset> : null}
      <DistributionFeedback error={recovery.error ?? distributionError} />
      {recovery.request ? <OptimizationRecovery count={recovery.request.orderIds.length} working={recovery.working}
        onConsult={() => void recovery.consult()} onRetry={() => void recovery.retry()} /> : null}
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
          </div> : <p className="entity-form-help">A otimização pode usar de 1 a 10 caminhões. Só será salva uma proposta que comporte todos os volumes, até o limite de 200. Disponibilidade não significa reserva da frota.</p>}

          <PlanOrderSelection readyOrders={readyOrders} selectedOrders={selectedOrders} customerNames={customerNames}
            isCalculating={isCalculating} selectedVolumeCount={selectedVolumeCount} hasUnknownVolumeCounts={hasUnknownVolumeCounts}
            exceedsVolumeLimit={exceedsVolumeLimit} maxVolumes={MAX_SYNC_VOLUMES} onToggle={toggleOrder} />
          <PlanCalculateAction selectedCount={selectedOrders.length} isCalculating={isCalculating}
            canCalculate={canCalculate} mode={mode} onCalculate={() => void handleCalculate()} />
        </>
      ) : null}
    </div>
  );
}
