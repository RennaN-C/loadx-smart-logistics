import { useRef, useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { ApiError } from "../../../types/api";
import type { CustomerListItem } from "../../customers/types";
import type { Product } from "../../products/types";
import { changeOrderStatus, createOrder, updateOrder } from "../api/ordersApi";
import { MANUAL_STATUS_TRANSITIONS, ORDER_PRIORITIES, type Order, type OrderStatus } from "../types";
import { isoToLocalInput, localInputToIso } from "./orderDateTime";
import { PRIORITY_LABELS, STATUS_LABELS } from "./orderLabels";
import { mapOrderErrorToMessage } from "./ordersErrorMessages";

/**
 * A sequência de entrega NÃO mora aqui. O backend exige que todos os itens do
 * pedido compartilhem a mesma (`_validate_single_delivery_sequence`): ela é a
 * parada do pedido na rota, não uma ordem entre produtos. Um campo por item
 * convidava a divergir e devolvia 422.
 */
interface ItemDraft {
  key: string;
  productId: string;
  quantity: string;
}

function toInt(value: string): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

/**
 * Só as transições que o backend aceita manualmente aparecem. A partir de
 * PLANNED, IN_TRANSIT, DELIVERED ou CANCELED não há saída manual — quem move
 * dali é o planejamento, a viagem ou a entrega —, então o campo vira leitura.
 */
function renderStatusField(
  current: OrderStatus,
  selected: OrderStatus,
  onChange: (status: OrderStatus) => void,
) {
  const targets = MANUAL_STATUS_TRANSITIONS[current];

  if (!targets) {
    return (
      <FormField id="order-status" label="SITUAÇÃO" hint="Alterada pelo sistema." narrow>
        <input id="order-status" value={STATUS_LABELS[current]} readOnly />
      </FormField>
    );
  }

  return (
    <FormField id="order-status" label="SITUAÇÃO" narrow>
      <select
        id="order-status"
        name="status"
        value={selected}
        onChange={(event) => onChange(event.target.value as OrderStatus)}
      >
        {[current, ...targets].map((value) => (
          <option key={value} value={value}>
            {STATUS_LABELS[value]}
          </option>
        ))}
      </select>
    </FormField>
  );
}

interface OrderFormProps {
  /** Ausente = criação. Presente = edição do pedido informado. */
  readonly order?: Order;
  readonly customers: readonly CustomerListItem[];
  readonly products: readonly Product[];
  readonly onSaved: () => void;
  readonly onCancel: () => void;
}

export function OrderForm({ order, customers, products, onSaved, onCancel }: OrderFormProps) {
  const isEditing = order !== undefined;
  const nextKey = useRef(0);
  const makeKey = () => {
    nextKey.current += 1;
    return `item-${nextKey.current}`;
  };

  const [customerId, setCustomerId] = useState(order?.customerId ?? "");
  const [priority, setPriority] = useState(order?.priority ?? "NORMAL");
  const [deliveryAddress, setDeliveryAddress] = useState(order?.deliveryAddress ?? "");
  const [expectedDeliveryAt, setExpectedDeliveryAt] = useState(
    isoToLocalInput(order?.expectedDeliveryAt ?? null),
  );
  const [status, setStatus] = useState<OrderStatus>(order?.status ?? "DRAFT");
  // uma por PEDIDO: todos os itens vão com este valor
  const [deliverySequence, setDeliverySequence] = useState(
    String(order?.items[0]?.deliverySequence ?? 1),
  );
  const [items, setItems] = useState<ItemDraft[]>(() =>
    order && order.items.length > 0
      ? order.items.map((item) => ({
          key: makeKey(),
          productId: item.productId,
          quantity: String(item.quantity),
        }))
      : [{ key: makeKey(), productId: "", quantity: "1" }],
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function updateItem(key: string, patch: Partial<ItemDraft>) {
    setItems((current) => current.map((item) => (item.key === key ? { ...item, ...patch } : item)));
  }

  function addItem() {
    setItems((current) => [
      ...current,
      { key: makeKey(), productId: "", quantity: "1" },
    ]);
  }

  function removeItem(key: string) {
    setItems((current) => current.filter((item) => item.key !== key));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    const payload = {
      customerId,
      priority,
      deliveryAddress: deliveryAddress.trim(),
      expectedDeliveryAt: localInputToIso(expectedDeliveryAt),
      items: items.map((item) => ({
        productId: item.productId,
        quantity: toInt(item.quantity),
        deliverySequence: toInt(deliverySequence),
      })),
    };

    try {
      if (order) {
        await updateOrder(order.id, payload);
        // Situação tem endpoint próprio (OC52); o PATCH genérico recusa `status`.
        if (status !== order.status) {
          await changeOrderStatus(order.id, status);
        }
      } else {
        await createOrder(payload);
      }
      onSaved();
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapOrderErrorToMessage(apiError));
      setIsSubmitting(false);
    }
  }

  return (
    <form className="entity-form" onSubmit={handleSubmit}>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <fieldset disabled={isSubmitting} className="entity-form-fieldset">
        <div className="entity-form-row">
          <FormField id="order-customer" label="CLIENTE">
            <select
              id="order-customer"
              name="customerId"
              required
              value={customerId}
              onChange={(event) => setCustomerId(event.target.value)}
            >
              <option value="">Selecione o cliente</option>
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name} — {customer.city}/{customer.state}
                </option>
              ))}
            </select>
          </FormField>
          <FormField id="order-priority" label="PRIORIDADE" narrow>
            <select
              id="order-priority"
              name="priority"
              value={priority}
              onChange={(event) => setPriority(event.target.value)}
            >
              {ORDER_PRIORITIES.map((value) => (
                <option key={value} value={value}>
                  {PRIORITY_LABELS[value]}
                </option>
              ))}
            </select>
          </FormField>
          {/* situação anda junto: as três dizem em que pé o pedido está */}
          {isEditing && order ? renderStatusField(order.status, status, setStatus) : null}
        </div>

        <div className="entity-form-row">
          <FormField id="order-address" label="ENDEREÇO DE ENTREGA">
            <input
              id="order-address"
              name="deliveryAddress"
              required
              maxLength={255}
              placeholder="Av. Brasil, 500 — Sorocaba/SP"
              value={deliveryAddress}
              onChange={(event) => setDeliveryAddress(event.target.value)}
            />
          </FormField>
          {/* rótulo e dica curtos de propósito: quebrando em duas linhas eles
              esticavam a linha toda e deixavam um vão embaixo do endereço */}
          <FormField
            id="order-expected"
            label="PREVISÃO (OPCIONAL)"
            hint="Fuso do seu navegador."
            narrow
          >
            <input
              id="order-expected"
              name="expectedDeliveryAt"
              type="datetime-local"
              value={expectedDeliveryAt}
              onChange={(event) => setExpectedDeliveryAt(event.target.value)}
            />
          </FormField>
          <FormField
            id="order-sequence"
            label="SEQ. DE ENTREGA"
            hint="Parada do pedido na rota."
            narrow
          >
            <input
              id="order-sequence"
              type="number"
              min={1}
              required
              value={deliverySequence}
              onChange={(event) => setDeliverySequence(event.target.value)}
            />
          </FormField>
        </div>

        <p className="field-label">ITENS DO PEDIDO</p>
        <div className="entity-form-box">
          <ul className="order-items">
            {items.map((item, index) => (
              <li key={item.key} className="order-item">
                <FormField id={`${item.key}-product`} label={`PRODUTO ${index + 1}`}>
                  <select
                    id={`${item.key}-product`}
                    required
                    value={item.productId}
                    onChange={(event) => updateItem(item.key, { productId: event.target.value })}
                  >
                    <option value="">Selecione o produto</option>
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.code} — {product.name}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField id={`${item.key}-quantity`} label="QTD." narrow>
                  <input
                    id={`${item.key}-quantity`}
                    type="number"
                    min={1}
                    required
                    value={item.quantity}
                    onChange={(event) => updateItem(item.key, { quantity: event.target.value })}
                  />
                </FormField>
                <button
                  type="button"
                  className="btn-link order-item-remove"
                  onClick={() => removeItem(item.key)}
                  disabled={items.length === 1}
                  title={items.length === 1 ? "O pedido precisa de pelo menos um item" : undefined}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>

          <div className="order-items-foot">
            <button type="button" className="btn-secondary" onClick={addItem}>
              + Adicionar item
            </button>
            <p className="entity-form-help">
              Todos os itens deste pedido descem juntos, na parada indicada acima. O otimizador usa
              essa parada para decidir o que entra por último no caminhão.
            </p>
          </div>
        </div>
      </fieldset>

      <div className="entity-form-actions">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancelar
        </button>
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="spinner" aria-hidden="true" />
              <span>Salvando…</span>
            </>
          ) : (
            <span>{isEditing ? "Salvar alterações" : "Cadastrar pedido"}</span>
          )}
        </button>
      </div>
    </form>
  );
}
