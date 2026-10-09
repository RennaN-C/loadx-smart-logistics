import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../../../types/api";
import { getLoadPlan } from "../../load-planning/api/loadPlansApi";
import type { LoadPlanItem } from "../../load-planning/types";
import { getLoadingSession } from "../api/loadingApi";
import { mapLoadingErrorToMessage } from "../components/loadingErrorMessages";
import type { LoadingSession } from "../types";

/** Um volume do checklist já com o produto que ele representa. */
export interface ChecklistRow {
  readonly itemId: string;
  readonly code: string;
  readonly checked: boolean;
  /** Ausente se o plano não trouxer o item — ver o comentário em `juntar`. */
  readonly product: LoadPlanItem | undefined;
}

export interface UseLoadingSessionResult {
  readonly session: LoadingSession | null;
  readonly rows: readonly ChecklistRow[];
  readonly pendingCount: number;
  readonly isLoading: boolean;
  readonly isWorking: boolean;
  readonly errorMessage: string | null;
  readonly run: (action: () => Promise<LoadingSession>) => Promise<void>;
  readonly reload: () => void;
}

/**
 * Junta o checklist com os itens do plano.
 *
 * `loading_session_items` guarda só `id`, `load_plan_item_id` e `status` — sem
 * nome nem código de produto. Um checklist de UUIDs não serve para quem está
 * conferindo caixa por caixa, então o produto vem do plano, ligado por
 * `load_plan_item_id`. É junção de APRESENTAÇÃO: nada aqui decide o que pode
 * ser conferido, que continua sendo do backend.
 *
 * A ordem é a de CARREGAMENTO, calculada pelo backend — é a ordem em que os
 * volumes entram no caminhão, que é como o conferente vai encontrá-los.
 */
function juntar(session: LoadingSession, planItems: readonly LoadPlanItem[]): ChecklistRow[] {
  const porId = new Map(planItems.map((item) => [item.id, item]));

  return session.items
    .map((item) => ({
      itemId: item.id,
      code: item.code,
      checked: item.status === "CHECKED",
      product: porId.get(item.loadPlanItemId),
    }))
    .sort((a, b) => (a.product?.loadingSequence ?? 0) - (b.product?.loadingSequence ?? 0));
}

export function useLoadingSession(sessionId: string | undefined): UseLoadingSessionResult {
  const [session, setSession] = useState<LoadingSession | null>(null);
  const [planItems, setPlanItems] = useState<readonly LoadPlanItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);

  const currentId = useRef(sessionId);
  currentId.current = sessionId;

  const toMessage = useCallback(
    (error: unknown) =>
      mapLoadingErrorToMessage(
        error instanceof ApiError
          ? error
          : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
      ),
    [],
  );

  useEffect(() => {
    setSession(null);
    setPlanItems([]);
    if (!sessionId) return;

    let ativo = true;
    setIsLoading(true);
    setErrorMessage(null);

    getLoadingSession(sessionId)
      .then(async (carregada) => {
        if (!ativo) return;
        setSession(carregada);

        // O plano é secundário: sem ele o checklist perde o nome do produto,
        // mas continua conferível. Por isso a falha aqui não derruba a tela.
        const plano = await getLoadPlan(carregada.loadPlanId).catch(() => null);
        if (ativo && plano) setPlanItems(plano.items);
      })
      .catch((error) => {
        if (ativo) setErrorMessage(toMessage(error));
      })
      .finally(() => {
        if (ativo) setIsLoading(false);
      });

    return () => {
      ativo = false;
    };
  }, [sessionId, tentativa, toMessage]);

  const run = useCallback(
    async (action: () => Promise<LoadingSession>) => {
      setErrorMessage(null);
      setIsWorking(true);

      try {
        const updated = await action();
        if (currentId.current === updated.id) setSession(updated);
      } catch (error) {
        setErrorMessage(toMessage(error));
      } finally {
        setIsWorking(false);
      }
    },
    [toMessage],
  );

  const currentSession = session?.id === sessionId ? session : null;
  const rows = currentSession ? juntar(currentSession, planItems) : [];

  return {
    session: currentSession,
    rows,
    pendingCount: rows.filter((row) => !row.checked).length,
    isLoading,
    isWorking,
    errorMessage,
    run,
    reload: () => setTentativa((n) => n + 1),
  };
}
