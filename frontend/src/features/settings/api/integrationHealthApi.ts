import { api } from "../../../services/api";
export type HealthComponent = "api" | "database" | "whatsapp" | "ai" | "webhook" | "notifications";
export type HealthStatus = "AVAILABLE" | "SIMULATED" | "NOT_CONFIGURED" | "NOT_IMPLEMENTED" | "LIMITED" | "UNAVAILABLE" | "TIMEOUT";
export type HealthReason = "LIVE" | "READY" | "READINESS_FAILED" | "TIMEOUT" | "MOCK_PROVIDER" | "PROVIDER_NOT_IMPLEMENTED" | "OC83_PENDING" | "OC84_PENDING" | "NOT_CONFIGURED" | "APPROVAL_REQUIRED" | "PROVIDER_FAILED" | "INVALID_SIGNAL";
export interface ComponentHealth {
  component: HealthComponent;
  mode: "INTERNAL" | "MOCK" | "REAL";
  status: HealthStatus;
  configured: boolean | null;
  reason_code: HealthReason;
}
export interface IntegrationHealthReport {
  checked_at: string;
  correlation_id: string;
  overall_status: "PARTIAL" | "DEGRADED";
  components: ComponentHealth[];
}
export async function getIntegrationHealth(): Promise<IntegrationHealthReport> {
  const { data } = await api.get<IntegrationHealthReport>("/integration-health", { timeout: 8000 });
  return data;
}
