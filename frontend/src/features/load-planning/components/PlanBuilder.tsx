import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { useResourceList } from "../../../hooks/useResourceList";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import { listTrucks } from "../../trucks/api/trucksApi";
import { ApiError } from "../../../types/api";
import { createLoadPlan } from "../api/loadPlansApi";
import type { LoadPlan } from "../types";
import { mapLoadPlanErrorToMessage } from "./loadPlansErrorMessages";

interface PlanBuilderProps {
  readonly onCalculated: (plan: LoadPlan) => void;
}

export function PlanBuilder({ onCalculated }: PlanBuilderProps) {
  const { items: trucks, status: trucksStatus } = useResourceList(listTrucks);
  const { items: orders, status: ordersStatus } = useResourceList(listOrders);
  const { items: customers } = useResourceList(listCustomers);

  const [truckId, setTruckId] = useState("");
  const [selectedOrders, setSelectedOrders] = useState<string[]>([]);
  const [isCalculating, setIsCalculating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Só caminhão ativo carrega, e só pedido READY entra em plano (regra do backend).
  const activeTrucks = useMemo(() => trucks.filter((truck) => truck.active), [trucks]);
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
  const canCalculate = truckId !== "" && selectedOrders.length > 0 && !isCalculating;

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
              hint="Só caminhões ativos aparecem aqui."
            >
              <select id="plan-truck" value={truckId} onChange={(event) => setTruckId(event.target.value)}>
                <option value="">Selecione o caminhão</option>
                {activeTrucks.map((truck) => (
                  <option key={truck.id} value={truck.id}>
                    {truck.plate} — {truck.model} ({truck.internalLengthCm}×{truck.internalWidthCm}×
                    {truck.internalHeightCm} cm)
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
