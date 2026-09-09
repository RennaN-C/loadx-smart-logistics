import { useCallback, useState } from "react";

import { ApiError } from "../types/api";

export interface UseEditTargetResult<T> {
  target: T | null;
  /** Id em carregamento, para desabilitar só o botão daquele card. */
  loadingId: string | null;
  error: ApiError | null;
  open: (id: string) => Promise<void>;
  close: () => void;
}

/**
 * Abre o formulário de edição com o registro COMPLETO.
 *
 * As listagens de clientes, motoristas e pedidos devolvem um resumo — dado
 * pessoal e itens só saem no detalhe. Editar a partir do que veio na lista
 * enviaria um PATCH com campos faltando, então é preciso buscar por id antes.
 */
export function useEditTarget<T>(fetchDetail: (id: string) => Promise<T>): UseEditTargetResult<T> {
  const [target, setTarget] = useState<T | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const open = useCallback(
    async (id: string) => {
      setLoadingId(id);
      setError(null);

      try {
        setTarget(await fetchDetail(id));
      } catch (caught) {
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
        );
      } finally {
        setLoadingId(null);
      }
    },
    [fetchDetail],
  );

  const close = useCallback(() => {
    setTarget(null);
    setError(null);
  }, []);

  return { target, loadingId, error, open, close };
}
