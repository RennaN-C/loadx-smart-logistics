import { api } from "../../../services/api";

export interface ManagementFilters {
  start: string;
  end: string;
  truck_id?: string;
  driver_id?: string;
}

export interface ManagementSummary {
  start: string;
  end: string;
  trips_created: number;
  trips_started: number;
  trips_finished: number;
  deliveries_completed: number;
  orders_with_completed_leg: number;
  occurrences_registered: number;
  delivery_exceptions: number;
  trips_canceled: number;
  interruption_events: number;
}

export async function fetchManagementSummary(params: ManagementFilters): Promise<ManagementSummary> {
  const response = await api.get<ManagementSummary>("/reports/management-summary", { params });
  return response.data;
}

export async function downloadManagementReport(
  format: "csv" | "pdf",
  params: ManagementFilters,
): Promise<void> {
  const response = await api.get<Blob>(`/reports/management-summary.${format}`, {
    params,
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(response.data);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = `loadx-management.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    window.URL.revokeObjectURL(url);
  }
}
