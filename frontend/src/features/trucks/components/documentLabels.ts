import type { DocumentKind, DocumentStatus } from "../api/documentsApi";
export const documentKinds: Record<DocumentKind, string> = { CRLV: "CRLV", LICENSING: "Licenciamento", INSURANCE: "Seguro" };
export const documentStatuses: Record<DocumentStatus, string> = { VALID: "Válido", EXPIRING: "Vence em até 30 dias", EXPIRED: "Vencido", NOT_YET_VALID: "Emissão futura", SUPERSEDED: "Substituído" };
