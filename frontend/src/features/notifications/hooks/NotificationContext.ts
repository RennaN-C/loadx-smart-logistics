import { createContext, useContext } from "react";

export interface NotificationCounter {
  count: number | null;
  failed: boolean;
  synchronize: (count: number) => void;
  refresh: () => Promise<void>;
}
export const NotificationContext = createContext<NotificationCounter | null>(null);
export function useNotificationCounter(): NotificationCounter {
  const value = useContext(NotificationContext);
  if (!value) throw new Error("A central deve estar dentro do contexto de notificações.");
  return value;
}
