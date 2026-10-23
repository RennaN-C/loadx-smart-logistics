import { api } from "../../../services/api";

export interface TimelineEvent {
  id: string;
  source: string;
  kind: string;
  entity_id: string;
  occurred_at: string;
  actor_id: string | null;
  status_before: string | null;
  status_after: string | null;
}

export interface TimelinePage {
  items: TimelineEvent[];
  total: number;
  page: number;
  page_size: number;
}

export async function getTripTimeline(tripId: string, page = 1): Promise<TimelinePage> {
  const { data } = await api.get<TimelinePage>(
    `/trips/${encodeURIComponent(tripId)}/timeline`,
    { params: { page, page_size: 20 } },
  );
  return data;
}
