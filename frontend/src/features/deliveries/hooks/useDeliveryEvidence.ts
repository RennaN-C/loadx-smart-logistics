import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type Page } from "../../../types/api";
import { getDeliveryReceipt, listDeliveryEvidences } from "../api/evidencesApi";
import type { DeliveryEvidence, DeliveryReceipt } from "../types";
import { mapEvidenceErrorToMessage } from "../components/evidenceErrorMessages";

export function evidenceError(error: unknown): string {
  return mapEvidenceErrorToMessage(error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Falha inesperada."));
}

export function useDeliveryEvidence(deliveryId: string) {
  const [receipt, setReceipt] = useState<DeliveryReceipt | null>(null);
  const [data, setData] = useState<Page<DeliveryEvidence> | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const request = useRef(0);
  const load = useCallback(async (requestedPage = 1) => {
    const current = ++request.current;
    setLoading(true); setError("");
    try {
      const loaded = await getDeliveryReceipt(deliveryId);
      if (current !== request.current) return;
      setReceipt(loaded);
      const result = await listDeliveryEvidences(deliveryId, { page: requestedPage, pageSize: 20 });
      if (current === request.current) { setData(result); setPage(requestedPage); }
    } catch (e) {
      if (current === request.current) { setData(null); setError(evidenceError(e)); }
    } finally { if (current === request.current) setLoading(false); }
  }, [deliveryId]);
  const invalidate = useCallback(() => { ++request.current; }, []);
  useEffect(() => { void load(); return invalidate; }, [load, invalidate]);
  return { receipt, data, page, loading, error, load };
}
