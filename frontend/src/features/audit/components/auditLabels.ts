import type { AuditEntityType, AuditEventType } from "../types";

export const AUDIT_ENTITY_LABELS: Record<AuditEntityType, string> = {
  ORDER: "Pedido",
  LOAD_PLAN: "Plano de carga",
  LOAD_DISTRIBUTION: "Distribuição de carga",
  LOAD_DISTRIBUTION_PART: "Parte da distribuição",
  TRIP: "Viagem",
  DELIVERY: "Entrega",
  USER: "Usuário",
  CUSTOMER: "Cliente",
  ATTACHMENT: "Anexo operacional",
  DRIVER_DOCUMENT: "Documento de motorista",
  DRIVER_DOCUMENT_POLICY: "Política documental de motorista",
  DRIVER_DOCUMENT_TYPE: "Tipo documental de motorista",
  TRUCK_DOCUMENT: "Documento de caminhão",
  TRUCK_DOCUMENT_POLICY: "Política documental",
  TRUCK_MAINTENANCE: "Manutenção de caminhão",
  CUSTOMER_ADDRESS: "Endereço de cliente",
  PRODUCT: "Produto",
  TRUCK: "Caminhão",
  DRIVER: "Motorista",
};

export const AUDIT_EVENT_LABELS: Record<AuditEventType, string> = {
  STATUS_CHANGED: "Situação alterada",
  USER_CREATED: "Usuário criado",
  USER_UPDATED: "Usuário atualizado",
  RECORD_ARCHIVED: "Cadastro arquivado",
  MAINTENANCE_CREATED: "Manutenção registrada",
  MAINTENANCE_CLOSED: "Manutenção encerrada",
  ATTACHMENT_REGISTERED: "Anexo registrado",
  ATTACHMENT_REVOKED: "Anexo removido",
  DRIVER_DOCUMENT_CREATED: "Documento de motorista registrado",
  DRIVER_DOCUMENT_RENEWED: "Documento de motorista renovado",
  DRIVER_DOCUMENT_POLICY_UPDATED: "Política de motorista atualizada",
  DRIVER_DOCUMENT_TYPE_APPROVED: "Tipo documental aprovado",
  TRUCK_DOCUMENT_CREATED: "Documento registrado",
  TRUCK_DOCUMENT_RENEWED: "Documento substituído",
  TRUCK_DOCUMENT_POLICY_UPDATED: "Política documental alterada",
  TRUCK_ODOMETER_UPDATED: "Quilometragem atualizada",
  CUSTOMER_ADDRESS_CREATED: "Endereço criado",
  CUSTOMER_ADDRESS_UPDATED: "Endereço atualizado",
  CUSTOMER_ADDRESS_ARCHIVED: "Endereço arquivado",
  CUSTOMER_ADDRESS_REACTIVATED: "Endereço reativado",
  RECORD_REACTIVATED: "Cadastro reativado",
};

const FIELD_LABELS: Readonly<Record<string, string>> = {
  active: "ativo",
  odometer_km: "quilometragem",
  next_service_at: "data da revisão",
  next_service_km: "quilometragem da revisão",
  closed_at: "encerramento",
  is_primary: "principal",
  label: "identificação",
  address: "endereço",
  city: "cidade",
  state: "UF",
  postal_code: "CEP",
  driver_id: "motorista vinculado",
  email: "e-mail",
  name: "nome",
  password: "senha",
  role: "perfil",
};

export function describeAuditEntry(entry: {
  readonly eventType: AuditEventType;
  readonly oldStatus: string | null;
  readonly newStatus: string | null;
  readonly changedFields: readonly string[];
}): string {
  if (entry.eventType === "STATUS_CHANGED") {
    const oldStatus = entry.oldStatus ?? "sem situação anterior";
    const newStatus = entry.newStatus ?? "situação não informada";
    return `${oldStatus} → ${newStatus}`;
  }

  if (entry.eventType === "USER_CREATED") {
    return "Cadastro administrativo criado.";
  }

  if (entry.changedFields.length === 0) {
    return "Cadastro administrativo atualizado.";
  }

  const fields = entry.changedFields.map((field) => FIELD_LABELS[field] ?? field);
  return `Campos alterados: ${fields.join(", ")}.`;
}
