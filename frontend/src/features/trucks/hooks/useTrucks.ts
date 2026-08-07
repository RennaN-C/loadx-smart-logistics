import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../types/api";
import { listTrucks } from "../api/trucksApi";
import type { Truck } from "../types";

export type TrucksStatus = "loading" | "success" | "error";

interface TrucksState {
  status: TrucksStatus;
  trucks: Truck[];
  error: ApiError | null;
}

export interface UseTrucksResult extends TrucksState {
  refetch: () => Promise<void>;
}

export function useTrucks(): UseTrucksResult {
  const [state, setState] = useState<TrucksState>({
    status: "loading",
    trucks: [],
    error: null,
  });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, status: "loading", error: null }));

    try {
      const trucks = await listTrucks();
      setState({ status: "success", trucks, error: null });
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setState({ status: "error", trucks: [], error: apiError });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...state, refetch: load };
}
