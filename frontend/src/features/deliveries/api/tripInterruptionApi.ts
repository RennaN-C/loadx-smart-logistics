import { api } from "../../../services/api";

export interface TripInterruptionEvent {
  id: string;
  trip_id: string;
  actor_id: string;
  idempotency_key: string;
  action: "INTERRUPTED" | "RESUMED";
  reason: string;
  created_at: string;
  trip_status: "INTERRUPTED" | "IN_ROUTE";
}

export async function listTripInterruptions(id: string): Promise<TripInterruptionEvent[]> {
  const { data } = await api.get<TripInterruptionEvent[]>(`/trips/${id}/interruptions`);
  return data;
}

export async function changeTripInterruption(
  id: string,
  action: "INTERRUPTED" | "RESUMED",
  reason: string,
  idempotencyKey: string,
): Promise<TripInterruptionEvent> {
  const endpoint = action === "INTERRUPTED" ? "interruptions" : "resumptions";
  const { data } = await api.post<TripInterruptionEvent>(
    `/trips/${id}/${endpoint}`,
    { reason, idempotency_key: idempotencyKey },
  );
  return data;
}
