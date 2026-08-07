import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../types/api";
import { listProducts } from "../api/productsApi";
import type { Product } from "../types";

export type ProductsStatus = "loading" | "success" | "error";

interface ProductsState {
  status: ProductsStatus;
  products: Product[];
  error: ApiError | null;
}

export interface UseProductsResult extends ProductsState {
  refetch: () => Promise<void>;
}

export function useProducts(): UseProductsResult {
  const [state, setState] = useState<ProductsState>({
    status: "loading",
    products: [],
    error: null,
  });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, status: "loading", error: null }));

    try {
      const products = await listProducts();
      setState({ status: "success", products, error: null });
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setState({ status: "error", products: [], error: apiError });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...state, refetch: load };
}
