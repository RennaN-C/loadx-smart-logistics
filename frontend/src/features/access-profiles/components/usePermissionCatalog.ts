import { useEffect, useState } from "react";
import { permissionCatalog, type PermissionDefinition } from "../api/profilesApi";

export function usePermissionCatalog(enabled = true) {
  const [items, setItems] = useState<PermissionDefinition[]>([]);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let current = true;
    setStatus("loading");
    permissionCatalog().then((data) => { if (current) { setItems(data); setStatus("success"); } }).catch(() => { if (current) setStatus("error"); });
    return () => { current = false; };
  }, [enabled, attempt]);
  return { items, status, retry: () => setAttempt((value) => value + 1) };
}
