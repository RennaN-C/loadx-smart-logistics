import { ApiError } from "../../../types/api";
import { useEffect, useState } from "react";
import type { PermissionSubject } from "../../auth/permissions";
import { searchRecords, type SearchResult } from "../api/searchApi";
import { visibleResults } from "./searchPresentation";

export type SearchStatus = "idle" | "loading" | "ready" | "error" | "forbidden";
export function useSearchResults(query: string, role: PermissionSubject) {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [status, setStatus] = useState<SearchStatus>("idle");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    setResults([]);
    if (query.length < 2 || query.length > 120) { setStatus("idle"); return; }
    let current = true;
    const controller = new AbortController();
    setStatus("loading");
    const timer = window.setTimeout(() => {
      searchRecords(query, controller.signal).then((items) => {
        if (!current) return;
        setResults(visibleResults(items, role)); setStatus("ready");
      }).catch((error: unknown) => {
        if (!current) return;
        const forbidden = error instanceof ApiError && (error.status === 403 || error.code === "AUTH_FORBIDDEN");
        setStatus(forbidden ? "forbidden" : "error");
      });
    }, 300);
    return () => { current = false; controller.abort(); window.clearTimeout(timer); };
  }, [query, attempt, role]);
  return { results, status, retry: () => setAttempt((value) => value + 1) };
}
