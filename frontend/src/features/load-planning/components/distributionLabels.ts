import type { DistributionStatus } from "../types";
export const DISTRIBUTION_LABELS: Record<DistributionStatus, string> = {
  PROPOSED: "Proposta salva", PARTIALLY_APPROVED: "Parcialmente aprovada",
  APPROVED: "Aprovada", INCOMPLETE: "Incompleta", CANCELED: "Cancelada",
};
export const PART_LABELS = { PENDING: "Aguardando aprovação", APPROVED: "Parte aceita", CANCELED: "Precisa reprocessar" };
