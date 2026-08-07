import { api } from "../../../services/api";
import type { Order, OrderInput, OrderItem, OrderStatus, OrderUpdateInput } from "../types";

interface OrderItemDto {
  id: string;
  order_id: string;
  product_id: string;
  quantity: number;
  delivery_sequence: number;
}

interface OrderDto {
  id: string;
  customer_id: string;
  status: OrderStatus;
  priority: string;
  delivery_address: string;
  expected_delivery_at: string | null;
  created_at: string;
  items: OrderItemDto[];
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
  if (input.status !== undefined) dto.status = input.status;
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

export async function listOrders(): Promise<Order[]> {
  const { data } = await api.get<OrderDto[]>("/orders");

  return data.map(mapOrderFromDto);
}

export async function createOrder(input: OrderInput): Promise<Order> {
  const { data } = await api.post<OrderDto>("/orders", mapOrderToDto(input));

  return mapOrderFromDto(data);
}

export async function updateOrder(id: string, input: OrderUpdateInput): Promise<Order> {
  const { data } = await api.patch<OrderDto>(`/orders/${id}`, mapOrderToDto(input));

  return mapOrderFromDto(data);
}
