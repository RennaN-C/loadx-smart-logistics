import { StatusPill } from "../../../components/StatusPill";
import type { OrderListItem } from "../types";
import { priorityLabel, STATUS_LABELS, statusTone } from "./orderLabels";

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

interface OrderCardProps {
  readonly order: OrderListItem;
  /** Resolvido na página: a listagem só traz o id do cliente. */
  readonly customerName: string;
  readonly canManage: boolean;
  readonly isOpening: boolean;
  readonly onEdit: (id: string) => void;
}

/**
 * Mostra só o que a listagem entrega. Endereço e itens ficam no detalhe
 * (`GET /orders/{id}`), então o card exibe a contagem em vez da lista.
 */
export function OrderCard({ order, customerName, canManage, isOpening, onEdit }: OrderCardProps) {
  return (
    <article className="order-card">
      <div className="order-card-head">
        <p className="order-card-customer">{customerName}</p>
        <StatusPill tone={statusTone(order.status)}>{STATUS_LABELS[order.status]}</StatusPill>
      </div>

      <dl className="order-card-meta">
        <div>
          <dt>PRIORIDADE</dt>
          <dd>{priorityLabel(order.priority)}</dd>
        </div>
        <div>
          <dt>ITENS</dt>
          <dd>{order.itemCount}</dd>
        </div>
        <div>
          <dt>PREVISÃO</dt>
          <dd>
            {order.expectedDeliveryAt ? dateFormatter.format(new Date(order.expectedDeliveryAt)) : "—"}
          </dd>
        </div>
      </dl>

      {canManage ? (
        <div className="order-card-foot">
          <button
            type="button"
            className="btn-link"
            disabled={isOpening}
            onClick={() => onEdit(order.id)}
          >
            {isOpening ? "Abrindo…" : "Editar"}
          </button>
        </div>
      ) : null}
    </article>
  );
}
