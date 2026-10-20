import { Link } from "react-router-dom";
import type { OrderListItem } from "../../orders/types";

function orderVolumeLabel(count?: number): string {
  if (count === undefined) return "volumes não informados";
  return `${count} ${count === 1 ? "volume" : "volumes"}`;
}

export function PlanOrderSelection({ readyOrders, selectedOrders, customerNames, isCalculating,
  selectedVolumeCount, hasUnknownVolumeCounts, exceedsVolumeLimit, maxVolumes, onToggle }: {
  readonly readyOrders: OrderListItem[]; readonly selectedOrders: string[];
  readonly customerNames: Map<string, string>; readonly isCalculating: boolean;
  readonly selectedVolumeCount: number; readonly hasUnknownVolumeCounts: boolean;
  readonly exceedsVolumeLimit: boolean; readonly maxVolumes: number;
  readonly onToggle: (id: string) => void;
}) {
  return <>
          <p className="field-label">PEDIDOS A CARREGAR</p>
          <p className="entity-form-help">
            Só pedidos com situação <strong>Pronto</strong> entram em um plano. Aprovar o plano move todos
            eles para Planejado. O cálculo aceita até {maxVolumes} volumes físicos por plano;
            um item pode conter várias unidades.
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
                      disabled={isCalculating}
                      checked={selectedOrders.includes(order.id)}
                      onChange={() => onToggle(order.id)}
                    />
                    <span>
                      {customerNames.get(order.customerId) ?? "Cliente não encontrado"}
                      <small>
                        Pedido {order.id.slice(0, 8)} · {order.itemCount} {order.itemCount === 1 ? "item" : "itens"}
                        {" · "}{orderVolumeLabel(order.volumeCount)}
                      </small>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}

          <output className="plan-volume-summary" aria-live="polite" data-over-limit={exceedsVolumeLimit}>
            <strong>{selectedVolumeCount} de {maxVolumes} volumes físicos</strong>
            <span>{selectedOrders.length} {selectedOrders.length === 1 ? "pedido selecionado" : "pedidos selecionados"}
              {hasUnknownVolumeCounts ? " · algumas quantidades indisponíveis (validação no servidor)" : ""}
            </span>
          </output>
          {exceedsVolumeLimit ? (
            <div className="plan-volume-limit" role="alert">
              A seleção possui {selectedVolumeCount} volumes, acima do limite de {maxVolumes} por cálculo.
              Desmarque pedidos até ficar dentro do limite. Se um único pedido ultrapassar {maxVolumes},
              revise suas quantidades na tela de <Link to="/orders">Pedidos</Link>.
              O sistema não divide pedidos automaticamente.
            </div>
          ) : null}
  </>;
}
