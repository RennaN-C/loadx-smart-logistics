import { Avatar } from "../../../components/Avatar";
import { Icon } from "../../../components/Icon";
import { StatusPill } from "../../../components/StatusPill";
import type { OrderListItem } from "../types";
import { priorityIsUrgent, priorityLabel, STATUS_LABELS, statusTone } from "./orderLabels";

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
        <div className="order-card-who">
          <Avatar name={customerName} size={34} />
          <p className="order-card-customer">{customerName}</p>
        </div>
        <StatusPill tone={statusTone(order.status)}>{STATUS_LABELS[order.status]}</StatusPill>
      </div>

      <dl className="order-card-meta">
        <div>
          <dt>
            <Icon name="priority" size={12} />
            PRIORIDADE
          </dt>
          <dd className={priorityIsUrgent(order.priority) ? "order-card-urgent" : undefined}>
            {priorityLabel(order.priority)}
          </dd>
        </div>
        <div>
          <dt>
            <Icon name="package" size={12} />
            ITENS
          </dt>
          <dd>{order.itemCount}</dd>
        </div>
        <div>
          <dt>
            <Icon name="calendar" size={12} />
            PREVISÃO
          </dt>
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
            <Icon name="edit" size={15} />
            {isOpening ? "Abrindo…" : "Editar"}
          </button>
        </div>
      ) : null}
    </article>
  );
}
