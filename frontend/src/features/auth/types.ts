import type { MfaChallenge } from "./mfaTypes";
export type Role = "ADMIN" | "LOGISTICS_MANAGER" | "CHECKER" | "DRIVER";

export interface AuthenticatedUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  active: boolean;
  createdAt: string;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  status: AuthStatus;
  user: AuthenticatedUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: AuthenticatedUser | null, accountNotice?: "password-changed" | "session-revoked") => void;
  pendingMfa?: MfaChallenge;
  beginMfa?: (challenge: MfaChallenge | undefined) => void;
  accountNotice?: "password-changed" | "session-revoked";
}
