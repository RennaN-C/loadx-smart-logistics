import { StatusPill } from "../../../components/StatusPill";
import type { Order } from "../types";
import { priorityLabel, STATUS_LABELS, statusTone } from "./orderLabels";

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

interface OrderCardProps {
  readonly order: Order;
  /** Resolvidos na página: o pedido só traz os ids. */
  readonly customerName: string;
  readonly productLabelOf: (productId: string) => string;
  readonly canManage: boolean;
  readonly onEdit: (order: Order) => void;
}

export function OrderCard({ order, customerName, productLabelOf, canManage, onEdit }: OrderCardProps) {
  const totalUnits = order.items.reduce((sum, item) => sum + item.quantity, 0);
  const sortedItems = [...order.items].sort((a, b) => a.deliverySequence - b.deliverySequence);

  return (
    <article className="order-card">
      <div className="order-card-head">
        <div>
          <p className="order-card-customer">{customerName}</p>
          <p className="order-card-address">{order.deliveryAddress}</p>
        </div>
        <StatusPill tone={statusTone(order.status)}>{STATUS_LABELS[order.status]}</StatusPill>
      </div>

      <dl className="order-card-meta">
        <div>
          <dt>PRIORIDADE</dt>
          <dd>{priorityLabel(order.priority)}</dd>
        </div>
        <div>
          <dt>ITENS</dt>
          <dd>
            {order.items.length} ({totalUnits} un.)
          </dd>
        </div>
        <div>
          <dt>PREVISÃO</dt>
          <dd>
            {order.expectedDeliveryAt ? dateFormatter.format(new Date(order.expectedDeliveryAt)) : "—"}
          </dd>
        </div>
      </dl>

      <ol className="order-card-items">
        {sortedItems.map((item) => (
          <li key={item.id}>
            <span className="order-card-seq">{item.deliverySequence}</span>
            <span className="order-card-product">{productLabelOf(item.productId)}</span>
            <span className="order-card-qty">×{item.quantity}</span>
          </li>
        ))}
      </ol>

      {canManage ? (
        <div className="order-card-foot">
          <button type="button" className="btn-link" onClick={() => onEdit(order)}>
            Editar
          </button>
        </div>
      ) : null}
    </article>
  );
}
