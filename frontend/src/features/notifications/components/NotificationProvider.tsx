import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { getUnreadCount } from "../api/notificationsApi";
import { NotificationContext } from "../hooks/NotificationContext";

export function NotificationProvider({ children, active }: { readonly children: ReactNode; readonly active: boolean }) {
  const [count, setCount] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);
  const revision = useRef(0);
  const { pathname } = useLocation();
  const synchronize = useCallback((value: number) => {
    revision.current += 1;
    setCount(value); setFailed(false);
  }, []);
  const refresh = useCallback(async () => {
    const request = ++revision.current;
    try {
      const result = await getUnreadCount();
      if (request === revision.current) { setCount(result); setFailed(false); }
    } catch {
      if (request === revision.current) { setCount(null); setFailed(true); }
    }
  }, []);
  useEffect(() => {
    if (!active) return;
    void refresh();
    const updateWhenVisible = () => { if (!document.hidden) void refresh(); };
    window.addEventListener("focus", updateWhenVisible);
    const timer = window.setInterval(updateWhenVisible, 60_000);
    return () => { revision.current += 1; window.clearInterval(timer); window.removeEventListener("focus", updateWhenVisible); };
  }, [active, pathname, refresh]);
  const value = useMemo(() => ({ count, failed, synchronize, refresh }), [count, failed, synchronize, refresh]);
  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}
