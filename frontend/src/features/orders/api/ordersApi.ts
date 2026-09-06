import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type {
  Order,
  OrderInput,
  OrderItem,
  OrderListItem,
  OrderPriority,
  OrderStatus,
  OrderUpdateInput,
} from "../types";

interface OrderItemDto {
  id: string;
  order_id: string;
  product_id: string;
  quantity: number;
  delivery_sequence: number;
}

/** Resumo da listagem: sem endereço e sem itens (ver OrderListRead no backend). */
interface OrderListDto {
  id: string;
  customer_id: string;
  status: OrderStatus;
  priority: OrderPriority;
  expected_delivery_at: string | null;
  created_at: string;
  item_count: number;
}

interface OrderDto {
  id: string;
  customer_id: string;
  status: OrderStatus;
  priority: OrderPriority;
  delivery_address: string;
  expected_delivery_at: string | null;
  created_at: string;
  items: OrderItemDto[];
}

export function mapOrderListItemFromDto(dto: OrderListDto): OrderListItem {
  return {
    id: dto.id,
    customerId: dto.customer_id,
    status: dto.status,
    priority: dto.priority,
    expectedDeliveryAt: dto.expected_delivery_at,
    createdAt: dto.created_at,
    itemCount: dto.item_count,
  };
}

function mapItemFromDto(dto: OrderItemDto): OrderItem {
  return {
    id: dto.id,
    orderId: dto.order_id,
    productId: dto.product_id,
    quantity: dto.quantity,
    deliverySequence: dto.delivery_sequence,
  };
}

export function mapOrderFromDto(dto: OrderDto): Order {
  return {
    id: dto.id,
    customerId: dto.customer_id,
    status: dto.status,
    priority: dto.priority,
    deliveryAddress: dto.delivery_address,
    expectedDeliveryAt: dto.expected_delivery_at,
    createdAt: dto.created_at,
    items: dto.items.map(mapItemFromDto),
  };
}

function mapOrderToDto(input: OrderUpdateInput): Record<string, unknown> {
  const dto: Record<string, unknown> = {};

  if (input.customerId !== undefined) dto.customer_id = input.customerId;
  if (input.priority !== undefined) dto.priority = input.priority;
  if (input.deliveryAddress !== undefined) dto.delivery_address = input.deliveryAddress;
  if (input.expectedDeliveryAt !== undefined) dto.expected_delivery_at = input.expectedDeliveryAt;
  if (input.items !== undefined) {
    dto.items = input.items.map((item) => ({
      product_id: item.productId,
      quantity: item.quantity,
      delivery_sequence: item.deliverySequence,
    }));
  }

  return dto;
}

export async function listOrders(params: ListParams = {}): Promise<Page<OrderListItem>> {
  const { data } = await api.get<PageDto<OrderListDto>>("/orders", { params: toPageQuery(params) });

  return mapPageFromDto(data, mapOrderListItemFromDto);
}

/** Necessário para editar: a listagem não traz endereço nem os itens. */
export async function getOrder(id: string): Promise<Order> {
  const { data } = await api.get<OrderDto>(`/orders/${id}`);

  return mapOrderFromDto(data);
}

export async function createOrder(input: OrderInput): Promise<Order> {
  const { data } = await api.post<OrderDto>("/orders", mapOrderToDto(input));

  return mapOrderFromDto(data);
}

export async function updateOrder(id: string, input: OrderUpdateInput): Promise<Order> {
  const { data } = await api.patch<OrderDto>(`/orders/${id}`, mapOrderToDto(input));

  return mapOrderFromDto(data);
}

/**
 * Situação tem endpoint próprio desde a OC52: `OrderUpdate` usa `extra="forbid"`
 * e recusa `status` com 422. Transição inválida volta 409.
 */
export async function changeOrderStatus(id: string, status: OrderStatus): Promise<Order> {
  const { data } = await api.patch<OrderDto>(`/orders/${id}/status`, { status });

  return mapOrderFromDto(data);
}
