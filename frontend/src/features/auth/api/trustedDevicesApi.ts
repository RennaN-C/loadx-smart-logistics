import { api } from "../../../services/api";

export interface TrustedDevice {
  id: string;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  current: boolean;
}
export interface TrustedDevices {
  enabled: boolean;
  lifetime_days: number;
  items: TrustedDevice[];
}
export async function listTrustedDevices(): Promise<TrustedDevices> {
  const { data } = await api.get<TrustedDevices>("/auth/me/trusted-devices");
  return data;
}
export async function forgetCurrentDevice(): Promise<void> {
  await api.delete("/auth/me/trusted-devices/current");
}
export async function revokeTrustedDevice(id: string): Promise<void> {
  await api.delete(`/auth/me/trusted-devices/${encodeURIComponent(id)}`);
}
export async function revokeAllTrustedDevices(): Promise<void> {
  await api.post("/auth/me/trusted-devices/revoke-all");
}
