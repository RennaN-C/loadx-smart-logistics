import { api } from "../../../services/api";
import { mapPageFromDto, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";

export type NotificationCategory = "TRIPS" | "OCCURRENCES" | "SECURITY";
export interface NotificationItem {
  id: string;
  event_type: "TRIP_STARTED" | "OCCURRENCE_REGISTERED";
  category: NotificationCategory;
  title: string;
  summary: string;
  created_at: string;
  received_at: string;
  read_at: string | null;
}
export interface NotificationPage extends Page<NotificationItem> { unreadCount: number }
export interface NotificationFilters {
  page?: number;
  page_size?: number;
  sort_order?: "asc" | "desc";
  category?: NotificationCategory;
  read?: boolean;
}
export interface NotificationPreference {
  category: NotificationCategory;
  enabled: boolean;
  mandatory: boolean;
}
export async function listNotifications(filters: NotificationFilters = {}, signal?: AbortSignal): Promise<NotificationPage> {
  const { data } = await api.get<PageDto<NotificationItem> & { unread_count: number }>("/notifications", { params: filters, signal });
  return { ...mapPageFromDto(data, (item) => item), unreadCount: data.unread_count };
}
export async function getUnreadCount(signal?: AbortSignal): Promise<number> {
  const { data } = await api.get<{ unread_count: number }>("/notifications/unread-count", { signal });
  return data.unread_count;
}
export async function markNotificationRead(id: string): Promise<NotificationItem> {
  const { data } = await api.post<NotificationItem>(`/notifications/${encodeURIComponent(id)}/read`);
  return data;
}
export async function markAllNotificationsRead(): Promise<number> {
  const { data } = await api.post<{ updated: number }>("/notifications/read-all");
  return data.updated;
}
export async function getNotificationSource(id: string): Promise<string> {
  const { data } = await api.get<{ href: string }>(`/notifications/${encodeURIComponent(id)}/source`);
  return data.href;
}
export async function getNotificationPreferences(): Promise<NotificationPreference[]> {
  const { data } = await api.get<{ items: NotificationPreference[] }>("/notifications/preferences");
  return data.items;
}
export async function saveNotificationPreferences(items: readonly NotificationPreference[]): Promise<NotificationPreference[]> {
  const { data } = await api.put<{ items: NotificationPreference[] }>("/notifications/preferences", {
    items: items.map(({ category, enabled }) => ({ category, enabled })),
  });
  return data.items;
}
