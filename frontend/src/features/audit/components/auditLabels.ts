import type { AuditEntityType, AuditEventType } from "../types";

export const AUDIT_ENTITY_LABELS: Record<AuditEntityType, string> = {
  ORDER: "Pedido",
  LOAD_PLAN: "Plano de carga",
  TRIP: "Viagem",
  DELIVERY: "Entrega",
  USER: "Usuário",
};

export const AUDIT_EVENT_LABELS: Record<AuditEventType, string> = {
  STATUS_CHANGED: "Situação alterada",
  USER_CREATED: "Usuário criado",
  USER_UPDATED: "Usuário atualizado",
};

const FIELD_LABELS: Readonly<Record<string, string>> = {
  active: "ativo",
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
