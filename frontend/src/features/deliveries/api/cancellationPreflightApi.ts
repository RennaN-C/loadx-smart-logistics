import { api } from "../../../services/api";

export interface CancellationPreflight {
  trip_id: string;
  safe_for_cancellation_workflow: boolean;
  blocking_reasons: string[];
  next_action: string;
}

export async function getCancellationPreflight(tripId: string): Promise<CancellationPreflight> {
  const { data } = await api.get<CancellationPreflight>(
    `/trips/${tripId}/cancellation-preflight`,
  );
  return data;
}


export interface TripCancellation {
  id: string;
  trip_id: string;
  actor_id: string;
  idempotency_key: string;
  reason: string;
  created_at: string;
  status: "CANCELED";
}

/** Server rechecks all locks and statuses; the preflight is not authority. */
export async function cancelScheduledTrip(
  tripId: string,
  reason: string,
  idempotencyKey: string,
): Promise<TripCancellation> {
  const { data } = await api.post<TripCancellation>(
    `/trips/${tripId}/cancellation`,
    { reason, idempotency_key: idempotencyKey },
  );
  return data;
}
