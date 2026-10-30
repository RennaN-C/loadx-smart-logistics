import { useEffect, useRef, useState } from "react";
import { ApiError } from "../../types/api";
import { optimizeDistribution, recoverOptimization } from "./api/distributionsApi";
import type { LoadDistribution } from "./types";

interface PendingRequest { key: string; orderIds: string[] }
const storageKey = (actor: string) => `loadx:optimization-request:v1:${actor}`;
function read(actor: string): PendingRequest | null {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(storageKey(actor)) ?? "null");
    if (!value || typeof value !== "object" || !("key" in value) || !("orderIds" in value)) return null;
    const { key, orderIds } = value;
    return typeof key === "string" && /^[0-9a-f-]{36}$/i.test(key)
      && Array.isArray(orderIds) && orderIds.length > 0 && orderIds.length <= 200
      && orderIds.every((id: unknown) => typeof id === "string" && id.length <= 36)
      ? { key, orderIds } : null;
  } catch { return null; }
}
function write(actor: string, request: PendingRequest | null) {
  try {
    if (request) sessionStorage.setItem(storageKey(actor), JSON.stringify(request));
    else sessionStorage.removeItem(storageKey(actor));
  } catch { /* Storage unavailable: keep the identity in memory for this mount. */ }
}
function definitivelyRejected(error: unknown): boolean {
  return error instanceof ApiError && error.status !== undefined && [400, 404, 409, 422].includes(error.status) && !["OPTIMIZATION_IN_PROGRESS", "IDEMPOTENCY_PAYLOAD_MISMATCH"].includes(error.code);
}

/** Metadata only. No automatic POST, plan cache, tokens or geometric data. */
export function useOptimizationRecovery(actor: string, onResult?: (value: LoadDistribution) => void) {
  const [state, setState] = useState(() => ({ actor, request: read(actor) }));
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<unknown>(null);
  // Um GET 404 após obter o lock do servidor permite oferecer descarte explícito
  // da referência LOCAL. Nunca inferir ausência a partir de POST 500/timeout.
  const [notFoundConfirmed, setNotFoundConfirmed] = useState(false);
  const busy = useRef(false);
  const currentActor = useRef(actor);
  currentActor.current = actor;
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const request = state.actor === actor ? state.request : read(actor);
  useEffect(() => { setState({ actor, request: read(actor) }); setError(null); setNotFoundConfirmed(false); }, [actor]);

  const isCurrent = () => alive.current && currentActor.current === actor;

  async function execute(value: PendingRequest, consult: boolean) {
    if (busy.current) return;
    busy.current = true; setWorking(true); setError(null); setNotFoundConfirmed(false);
    write(actor, value); setState({ actor, request: value });
    try {
      const result = consult ? await recoverOptimization(value.key) : await optimizeDistribution(value.orderIds, value.key);
      write(actor, null);
      if (isCurrent()) {
        setState({ actor, request: null }); onResult?.(result);
      }
    } catch (error_) {
      const clear = !consult && definitivelyRejected(error_);
      if (clear) write(actor, null);
      if (isCurrent()) {
        setError(error_);
        setNotFoundConfirmed(consult && error_ instanceof ApiError
          && error_.status === 404 && error_.code === "OPTIMIZATION_NOT_FOUND");
        if (clear) setState({ actor, request: null });
      }
    } finally {
      busy.current = false;
      if (isCurrent()) setWorking(false);
    }
  }
  return { request, working, error,
    // A referência só pode ser descartada após consulta explícita com 404.
    canDiscard: Boolean(request) && notFoundConfirmed && !working,
    discard: () => {
      if (!request || busy.current || working || !notFoundConfirmed) return;
      write(actor, null);
      setState({ actor, request: null });
      setNotFoundConfirmed(false);
      setError(null);
    },
    start: (orderIds: string[]) => {
      if (request || busy.current) return Promise.resolve();
      return execute({ key: crypto.randomUUID(), orderIds: [...orderIds] }, false);
    },
    consult: () => request ? execute(request, true) : Promise.resolve(),
    retry: () => request ? execute(request, false) : Promise.resolve(),
  };
}
