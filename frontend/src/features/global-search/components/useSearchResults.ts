import { useEffect, useState } from "react";
import type { Role } from "../../auth/types";
import { searchRecords, type SearchResult } from "../api/searchApi";
import { visibleResults } from "./searchPresentation";

export type SearchStatus = "idle" | "loading" | "ready" | "error";
export function useSearchResults(query: string, role: Role | undefined) {
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
      }).catch(() => { if (current) setStatus("error"); });
    }, 300);
    return () => { current = false; controller.abort(); window.clearTimeout(timer); };
  }, [query, attempt, role]);
  return { results, status, retry: () => setAttempt((value) => value + 1) };
}
