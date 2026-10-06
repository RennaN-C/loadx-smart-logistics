export const LOADING_SESSION_STATUSES = ["PENDING", "IN_PROGRESS", "FINISHED"] as const;
export type LoadingSessionStatus = (typeof LOADING_SESSION_STATUSES)[number];

export type LoadingItemStatus = "PENDING" | "CHECKED";

export interface LoadingSessionItem {
  id: string;
  /** Aponta para o item do plano de carga — é por aqui que se descobre o produto. */
  loadPlanItemId: string;
  status: LoadingItemStatus;
  /**
   * `loadx:loading-item:<uuid>`, 55 caracteres. O backend devolve pronto; o
   * frontend nunca monta esse texto, só o compara e o envia de volta.
   */
  code: string;
}

export interface LoadingSession {
  id: string;
  loadPlanId: string;
  status: LoadingSessionStatus;
  startedAt: string | null;
  finishedAt: string | null;
  items: LoadingSessionItem[];
}

/**
 * Próximo estado de cada etapa, para a tela não precisar repetir a regra.
 * `FINISHED` não tem sucessor: o carregamento termina ali.
 */
export const LOADING_TRANSITIONS: Partial<Record<LoadingSessionStatus, LoadingSessionStatus>> = {
  PENDING: "IN_PROGRESS",
  IN_PROGRESS: "FINISHED",
};
