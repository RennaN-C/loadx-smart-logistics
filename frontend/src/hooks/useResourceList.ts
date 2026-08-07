import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../types/api";

export type ResourceStatus = "loading" | "success" | "error";

interface ResourceState<T> {
  status: ResourceStatus;
  items: T[];
  error: ApiError | null;
}

export interface UseResourceListResult<T> extends ResourceState<T> {
  refetch: () => Promise<void>;
}

/**
 * Carga de uma lista completa vinda da API, com os três estados que toda tela de
 * cadastro precisa. Nenhum endpoint do backend aceita paginação ou filtro por
 * query param hoje, então buscar tudo e filtrar no cliente é o comportamento certo.
 *
 * `load` precisa ser uma referência estável — passar a função exportada do módulo
 * de API (`listTrucks`, `listProducts`, …) já satisfaz isso.
 */
export function useResourceList<T>(load: () => Promise<T[]>): UseResourceListResult<T> {
  const [state, setState] = useState<ResourceState<T>>({
    status: "loading",
    items: [],
    error: null,
  });

  const fetchAll = useCallback(async () => {
    setState((current) => ({ ...current, status: "loading", error: null }));

    try {
      const items = await load();
      setState({ status: "success", items, error: null });
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setState({ status: "error", items: [], error: apiError });
    }
  }, [load]);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  return { ...state, refetch: fetchAll };
}
