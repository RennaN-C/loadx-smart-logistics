import { api } from "../../../services/api";

export const DELIVERY_EXCEPTION_CODES = [
  "CUSTOMER_ABSENT",
  "REFUSED",
  "DAMAGED",
  "OPERATIONAL_FAILURE",
  "RESCHEDULED",
  "RESUMED",
] as const;

export type DeliveryExceptionCode = (typeof DELIVERY_EXCEPTION_CODES)[number];

export interface DeliveryException {
  id: string;
  delivery_id: string;
  trip_id: string;
  code: DeliveryExceptionCode;
  reason: string;
  actor_id: string;
  idempotency_key: string;
  scheduled_for: string | null;
  created_at: string;
}

interface RegisterExceptionInput {
  code: DeliveryExceptionCode;
  reason: string;
  idempotency_key: string;
  scheduled_for?: string;
}

/** Same idempotency key is retained across network retries by the caller. */
export async function registerDeliveryException(
  deliveryId: string,
  input: RegisterExceptionInput,
): Promise<DeliveryException> {
  const { data } = await api.post<DeliveryException>(
    `/deliveries/${deliveryId}/exceptions`,
    input,
  );
  return data;
}

export async function listDeliveryExceptions(
  deliveryId: string,
): Promise<DeliveryException[]> {
  const { data } = await api.get<DeliveryException[]>(
    `/deliveries/${deliveryId}/exceptions`,
  );
  return data;
}
