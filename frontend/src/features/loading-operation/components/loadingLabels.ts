import type { StatusTone } from "../../../components/StatusPill";
import type { LoadingSessionStatus } from "../types";

export const LOADING_STATUS_LABELS: Record<LoadingSessionStatus, string> = {
  PENDING: "Não iniciado",
  IN_PROGRESS: "Em conferência",
  FINISHED: "Concluído",
};

export function loadingStatusTone(status: LoadingSessionStatus): StatusTone {
  if (status === "FINISHED") return "good";
  return status === "IN_PROGRESS" ? "warn" : "neutral";
}
