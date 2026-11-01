import { Link } from "react-router-dom";

import { RowActions } from "../../../components/RowActions";
import { StatusPill } from "../../../components/StatusPill";
import type { OrderListItem, OrderStatus } from "../types";
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
  readonly onAttachments?: (id: string) => void;
  readonly onEdit: (id: string) => void;
  readonly onChangeStatus?: (id: string, status: OrderStatus) => void;
  readonly changingStatus?: boolean;
}

/**
 * Mostra só o que a listagem entrega. Endereço e itens ficam no detalhe
 * (`GET /orders/{id}`), então o card exibe a contagem em vez da lista.
 */
export function OrderCard({ order, customerName, canManage, isOpening, onEdit, onAttachments, onChangeStatus, changingStatus = false }: OrderCardProps) {
  return (
    <tr>
      <td data-label="Pedido"><Link className="btn-link" to={`/orders?order=${encodeURIComponent(order.id)}`}>{order.id.slice(0, 8)}</Link></td>
      <td data-label="Cliente"><strong>{customerName}</strong></td>
      <td data-label="Prioridade"><span className={priorityIsUrgent(order.priority) ? "order-card-urgent" : undefined}>
            {priorityLabel(order.priority)}
      </span></td>
      <td data-label="Itens">{order.itemCount}</td>
      <td data-label="Previsão">
            {order.expectedDeliveryAt ? dateFormatter.format(new Date(order.expectedDeliveryAt)) : "—"}
      </td>
      <td data-label="Situação"><StatusPill tone={statusTone(order.status)}>{STATUS_LABELS[order.status]}</StatusPill></td>
      <td data-label="Ações"><RowActions label={`Ações do pedido ${order.id.slice(0, 8)}`}>
        <Link className="btn-link" to={`/orders?order=${encodeURIComponent(order.id)}`}>Ver pedido</Link>
        {onAttachments ? <button type="button" className="btn-link" onClick={() => onAttachments(order.id)}>Anexos</button> : null}
        {canManage && (order.status === "DRAFT" || order.status === "READY") ? (
          <button type="button" className="btn-link" disabled={isOpening || changingStatus}
            onClick={() => onEdit(order.id)}>{isOpening ? "Abrindo…" : "Editar"}</button>
        ) : null}
        {canManage && onChangeStatus && order.status === "READY" ? (
          <button type="button" className="btn-link" disabled={changingStatus}
            onClick={() => onChangeStatus(order.id, "DRAFT")}>Voltar para rascunho</button>
        ) : null}
        {canManage && onChangeStatus && (order.status === "DRAFT" || order.status === "READY") ? (
          <button type="button" className="btn-link" disabled={changingStatus}
            onClick={() => onChangeStatus(order.id, "CANCELED")}>Cancelar pedido</button>
        ) : null}
      </RowActions></td>
    </tr>
  );
}
