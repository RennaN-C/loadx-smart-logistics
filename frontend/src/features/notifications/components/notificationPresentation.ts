import type { IconName } from "../../../components/Icon";
import type { NotificationCategory } from "../api/notificationsApi";

export const NOTIFICATION_CATEGORIES: Record<NotificationCategory, { label: string; icon: IconName }> = {
  TRIPS: { label: "Viagens", icon: "truck" },
  OCCURRENCES: { label: "Ocorrências", icon: "report" },
  SECURITY: { label: "Segurança", icon: "settings" },
};
