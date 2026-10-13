import { api } from "../../../services/api";
import { mapUserFromDto, type UserDto } from "./authApi";

export interface OwnSession {
  id: string;
  created_at: string;
  last_seen_at: string;
  idle_expires_at: string;
  absolute_expires_at: string;
  current: boolean;
}
export async function updateOwnProfile(name: string, email: string, identity?: { current_password: string; second_factor: string }) {
  const { data } = await api.patch<UserDto>("/auth/me", { name, email, ...identity });
  return mapUserFromDto(data);
}
export async function changeOwnPassword(current_password: string, new_password: string): Promise<void> {
  await api.post("/auth/me/password", { current_password, new_password });
}
export async function listOwnSessions(): Promise<OwnSession[]> {
  const { data } = await api.get<OwnSession[]>("/auth/me/sessions");
  return data;
}
export async function revokeOwnSession(id: string): Promise<void> {
  await api.delete(`/auth/me/sessions/${id}`);
}
export async function revokeOtherSessions(): Promise<void> {
  await api.post("/auth/me/sessions/revoke-others");
}
