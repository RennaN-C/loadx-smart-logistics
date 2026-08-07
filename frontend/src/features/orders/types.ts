export const ORDER_STATUSES = [
  "DRAFT",
  "READY",
  "PLANNED",
  "IN_TRANSIT",
  "DELIVERED",
  "CANCELED",
] as const;

export type OrderStatus = (typeof ORDER_STATUSES)[number];

/**
 * O backend aceita qualquer string de até 32 caracteres em `priority` — não há
 * enum lá. Estes valores são a convenção adotada no frontend enquanto a equipe
 * não define o contrato (`PENDENTE DE DEFINIÇÃO` em docs/11).
 */
export const ORDER_PRIORITIES = ["LOW", "NORMAL", "HIGH", "URGENT"] as const;

export type OrderPriority = (typeof ORDER_PRIORITIES)[number];

export interface OrderItem {
  id: string;
  orderId: string;
  productId: string;
  quantity: number;
  deliverySequence: number;
}

/**
 * A listagem devolve um resumo (`OrderListRead`): sem endereço de entrega e sem
 * os itens, só a contagem. O card usa `OrderListItem`; o formulário exige
 * `Order` completo, buscado por `GET /orders/{id}` na hora de editar.
 */
export interface OrderListItem {
  id: string;
  customerId: string;
  status: OrderStatus;
  priority: string;
  /** ISO 8601 em UTC, ou null. O backend exige fuso ao receber. */
  expectedDeliveryAt: string | null;
  createdAt: string;
  itemCount: number;
}

export interface Order extends Omit<OrderListItem, "itemCount"> {
  deliveryAddress: string;
  items: OrderItem[];
}

export interface OrderItemInput {
  productId: string;
  quantity: number;
  deliverySequence: number;
}

export interface OrderInput {
  customerId: string;
  priority: string;
  deliveryAddress: string;
  expectedDeliveryAt: string | null;
  items: OrderItemInput[];
}

export type OrderUpdateInput = Partial<OrderInput> & { status?: OrderStatus };
