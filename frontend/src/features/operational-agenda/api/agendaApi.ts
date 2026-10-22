import { api } from "../../../services/api";

export const agendaKinds = [
  "TRIP_CREATED", "TRIP_STARTED", "TRIP_FINISHED", "LOADING_STARTED",
  "LOADING_FINISHED", "DELIVERY_COMPLETED", "DELIVERY_EXCEPTION",
  "TRIP_CANCELED", "TRIP_INTERRUPTED", "TRIP_RESUMED",
] as const;
export type AgendaKind = typeof agendaKinds[number];

export interface AgendaItem {
  kind: AgendaKind;
  resource_id: string;
  trip_id: string;
  occurred_at: string;
  truck_id: string;
  driver_id: string;
}
export interface AgendaResponse {
  start: string;
  end: string;
  total: number;
  items: AgendaItem[];
}
export interface AgendaParams {
  start: string;
  end: string;
  kind?: AgendaKind;
  truck_id?: string;
  driver_id?: string;
}

export async function fetchAgenda(params: AgendaParams): Promise<AgendaResponse> {
  const { data } = await api.get<AgendaResponse>("/operations/agenda", { params });
  return data;
}
