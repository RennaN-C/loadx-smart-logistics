import { api } from "../../../services/api";
import { mapUserFromDto, type UserDto } from "./authApi";

import type { MfaChallenge, MfaStatus } from "../mfaTypes";
export type { MfaStatus } from "../mfaTypes";
export { MfaRequired } from "../mfaTypes";
export async function requestRecovery(email: string): Promise<void> { await api.post("/auth/password-recovery", { email }); }
export async function confirmRecovery(token: string, new_password: string): Promise<void> { await api.post("/auth/password-recovery/confirm", { token, new_password }); }
export async function setupMfa(challenge_token: string): Promise<string> {
  const { data } = await api.post<{ provisioning_uri: string }>("/auth/mfa/setup", { challenge_token }); return data.provisioning_uri;
}
export async function verifyMfa(challenge_token: string, code: string) {
  const { data } = await api.post<{ user: UserDto; recovery_codes: string[] }>("/auth/mfa/verify", { challenge_token, code });
  return { user: mapUserFromDto(data.user), codes: data.recovery_codes };
}
export async function getMfaStatus(): Promise<MfaStatus> { const { data } = await api.get<MfaStatus>("/auth/me/mfa"); return data; }
export async function enrollMfa(password: string): Promise<MfaChallenge> { const { data } = await api.post<MfaChallenge>("/auth/me/mfa/enroll", { password }); return data; }
export async function regenerateCodes(password: string, code: string): Promise<string[]> { const { data } = await api.post<{ recovery_codes: string[] }>("/auth/me/mfa/recovery-codes", { password, code }); return data.recovery_codes; }
export async function disableMfa(password: string, code: string): Promise<void> { await api.post("/auth/me/mfa/disable", { password, code }); }
