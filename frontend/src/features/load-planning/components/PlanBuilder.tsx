import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import type { ListParams } from "../../../services/pagination";
import { useResourceList } from "../../../hooks/useResourceList";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import { listTruckOperationalStatus, listTrucks } from "../../trucks/api/trucksApi";
import { ApiError } from "../../../types/api";
import { createLoadPlan } from "../api/loadPlansApi";
import type { LoadPlan } from "../types";
import { mapLoadPlanErrorToMessage } from "./loadPlansErrorMessages";

interface PlanBuilderProps {
  readonly onCalculated: (plan: LoadPlan) => void;
}

const listHistoricalCustomers = (params: ListParams) => listCustomers({ ...params, archiveStatus: "all" });

export function PlanBuilder({ onCalculated }: PlanBuilderProps) {
  const { items: trucks, status: trucksStatus } = useResourceList(listTrucks);
  // Duas consultas porque os dois contratos são diferentes: `GET /trucks` traz as
  // medidas internas, que são o que ajuda a escolher o baú; `operational-status`
  // traz a disponibilidade da OC67, e não traz medida nenhuma.
  const { items: situacoes } = useResourceList(listTruckOperationalStatus);
  const { items: orders, status: ordersStatus } = useResourceList(listOrders);
  const { items: customers } = useResourceList(listHistoricalCustomers);

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

  function toggleOrder(orderId: string) {
    setSelectedOrders((current) =>
      current.includes(orderId) ? current.filter((id) => id !== orderId) : [...current, orderId],
    );
  }

  async function handleCalculate() {
    setErrorMessage(null);
    setIsCalculating(true);

    try {
      onCalculated(await createLoadPlan({ truckId, orderIds: selectedOrders }));
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapLoadPlanErrorToMessage(apiError));
    } finally {
      setIsCalculating(false);
    }
  }

  const isLoading = trucksStatus === "loading" || ordersStatus === "loading";
  const canCalculate = activeTrucks.some((truck) => truck.id === truckId) && selectedOrders.length > 0 && !isCalculating;

  return (
    <div className="plan-builder">
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      {isLoading ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando caminhões e pedidos…</span>
        </p>
      ) : null}

      {!isLoading ? (
        <>
          <div className="entity-form-row">
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
          </div>

          <p className="field-label">PEDIDOS A CARREGAR</p>
          <p className="entity-form-help">
            Só pedidos com situação <strong>Pronto</strong> entram em um plano. Aprovar o plano move todos
            eles para Planejado.
          </p>

          {readyOrders.length === 0 ? (
            <p className="entity-state">
              Nenhum pedido pronto para planejar nesta página. Marque um pedido como Pronto na tela de
              Pedidos.
            </p>
          ) : (
            <ul className="plan-order-list">
              {readyOrders.map((order) => (
                <li key={order.id}>
                  <label htmlFor={`order-${order.id}`}>
                    <input
                      id={`order-${order.id}`}
                      type="checkbox"
                      checked={selectedOrders.includes(order.id)}
                      onChange={() => toggleOrder(order.id)}
                    />
                    <span>
                      {customerNames.get(order.customerId) ?? "Cliente não encontrado"}
                      <small>
                        {order.itemCount} {order.itemCount === 1 ? "item" : "itens"}
                      </small>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}

          <div className="entity-form-actions">
            <span className="plan-builder-count">
              {selectedOrders.length} {selectedOrders.length === 1 ? "pedido" : "pedidos"} selecionados
            </span>
            <button
              type="button"
              className="btn-primary"
              disabled={!canCalculate}
              onClick={() => void handleCalculate()}
            >
              {isCalculating ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  <span>Calculando…</span>
                </>
              ) : (
                <span>Calcular plano de carga</span>
              )}
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}
