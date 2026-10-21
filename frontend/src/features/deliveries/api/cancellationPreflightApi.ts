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
