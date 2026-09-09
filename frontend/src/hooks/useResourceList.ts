import { useCallback, useEffect, useState } from "react";

import { DEFAULT_PAGE_SIZE, type ListParams } from "../services/pagination";
import { ApiError, type Page } from "../types/api";

export type ResourceStatus = "loading" | "success" | "error";

interface ResourceState<T> {
  status: ResourceStatus;
  items: T[];
  error: ApiError | null;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface UseResourceListResult<T> extends ResourceState<T> {
  refetch: () => Promise<void>;
  goToPage: (page: number) => void;
}

const EMPTY = {
  items: [],
  pageSize: DEFAULT_PAGE_SIZE,
  total: 0,
  totalPages: 0,
};

/**
 * Carga paginada de uma coleção, com os três estados que toda tela de cadastro
 * precisa. Segue o envelope da ADR-017 (`items`/`page`/`total`/`total_pages`).
 *
 * Busca e filtro continuam no cliente e valem só para a página carregada: D12
 * mantém filtro server-side fora do contrato. Quem usa este hook deve deixar
 * isso explícito na tela, senão o usuário acha que buscou na base inteira.
 *
 * `load` precisa ser uma referência estável — passar a função exportada do
 * módulo de API (`listTrucks`, `listProducts`, …) já satisfaz isso.
 */
export function useResourceList<T>(
  load: (params: ListParams) => Promise<Page<T>>,
): UseResourceListResult<T> {
  const [requestedPage, setRequestedPage] = useState(1);
  const [state, setState] = useState<ResourceState<T>>({
    status: "loading",
    error: null,
    page: 1,
    ...EMPTY,
  });

  const fetchPage = useCallback(async () => {
    setState((current) => ({ ...current, status: "loading", error: null }));

    try {
      const result = await load({ page: requestedPage, pageSize: DEFAULT_PAGE_SIZE });
      setState({
        status: "success",
        items: result.items,
        error: null,
        page: result.page,
        pageSize: result.pageSize,
        total: result.total,
        totalPages: result.totalPages,
      });
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setState({ status: "error", error: apiError, page: requestedPage, ...EMPTY });
    }
  }, [load, requestedPage]);

  useEffect(() => {
    void fetchPage();
  }, [fetchPage]);

  return { ...state, refetch: fetchPage, goToPage: setRequestedPage };
}
