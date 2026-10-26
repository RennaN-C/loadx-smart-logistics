import type { ApiError } from "../../../types/api";

export function mapAuditErrorToMessage(error: ApiError): string {
  if (error.code === "AUTH_FORBIDDEN") {
    return "Seu perfil não possui permissão para consultar a auditoria.";
  }
  if (error.code === "AUDIT_INVALID_PERIOD" || error.code === "VALIDATION_ERROR") {
    return "Revise os filtros informados para a auditoria.";
  }
  if (error.code === "NETWORK_ERROR") {
    return "Não foi possível conectar ao servidor para consultar a auditoria.";
  }
  return "Não foi possível carregar o histórico de auditoria.";
}
