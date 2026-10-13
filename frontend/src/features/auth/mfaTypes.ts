export interface MfaChallenge { challenge_token: string; purpose: "ENROLL" | "LOGIN"; expires_at: string }
export interface MfaStatus { enabled: boolean; required: boolean }
export class MfaRequired extends Error {
  constructor(readonly challenge: MfaChallenge) { super("Segundo fator necessário"); }
}
