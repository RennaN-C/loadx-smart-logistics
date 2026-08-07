import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../types/api";
import { listTrucks } from "../api/trucksApi";
import type { Truck } from "../types";

export type TrucksStatus = "loading" | "success" | "error";
const PAGE_SIZE = 20;

interface TrucksState {
  status: TrucksStatus;
  trucks: Truck[];
  error: ApiError | null;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface UseTrucksResult extends TrucksState {
  refetch: () => Promise<void>;
  goToPage: (page: number) => void;
}

export function useTrucks(): UseTrucksResult {
  const [requestedPage, setRequestedPage] = useState(1);
  const [state, setState] = useState<TrucksState>({
    status: "loading",
    trucks: [],
    error: null,
    page: 1,
    pageSize: PAGE_SIZE,
    total: 0,
    totalPages: 0,
  });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, status: "loading", error: null }));

    try {
      const result = await listTrucks({ page: requestedPage, pageSize: PAGE_SIZE });
      setState({
        status: "success",
        trucks: result.items,
        error: null,
        page: result.page,
        pageSize: result.pageSize,
        total: result.total,
        totalPages: result.totalPages,
      });
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setState({
        status: "error",
        trucks: [],
        error: apiError,
        page: requestedPage,
        pageSize: PAGE_SIZE,
        total: 0,
        totalPages: 0,
      });
    }
  }, [requestedPage]);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...state, refetch: load, goToPage: setRequestedPage };
}
