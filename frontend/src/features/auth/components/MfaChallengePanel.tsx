import { useEffect, useState, type FormEvent } from "react";
import { MfaProvisioning } from "./MfaProvisioning";
import type { MfaChallenge } from "../mfaTypes";
import { setupMfa, verifyMfa } from "../api/identityApi";
import { useAuth } from "../hooks/useAuth";
import { accountError } from "./accountError";
import { RecoveryCodes } from "./RecoveryCodes";
import type { AuthenticatedUser } from "../types";
import "../pages/Identity.css";

export function MfaChallengePanel({ challenge }: { readonly challenge: MfaChallenge }) {
  const { updateUser, beginMfa } = useAuth();
  const [uri, setUri] = useState(""); const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const [completion, setCompletion] = useState<{ user: AuthenticatedUser; codes: string[] } | null>(null);
  const [expired, setExpired] = useState(() => Date.now() >= Date.parse(challenge.expires_at));
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (Date.now() >= Date.parse(challenge.expires_at)) {
        setExpired(true); setUri(""); setCode("");
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [challenge.expires_at]);
  async function provision() {
    if (uri || busy || expired || Date.now() >= Date.parse(challenge.expires_at)) return;
    setBusy(true); setError("");
    try {
      const provisioned = await setupMfa(challenge.challenge_token);
      if (Date.now() >= Date.parse(challenge.expires_at)) setExpired(true);
      else setUri(provisioned);
    }
    catch (e) { setError(accountError(e)); } finally { setBusy(false); }
  }
  async function verify(event: FormEvent) {
    event.preventDefault();
    if (expired || Date.now() >= Date.parse(challenge.expires_at)) return;
    setBusy(true); setError("");
    try { const result = await verifyMfa(challenge.challenge_token, code.trim()); setCode(""); setUri(""); if (result.codes.length) setCompletion(result); else updateUser(result.user); }
    catch (e) { setError(accountError(e)); } finally { setBusy(false); }
  }
  if (completion) return <div className="login-card identity-card"><RecoveryCodes codes={completion.codes} onDone={() => { updateUser(completion.user); setCompletion(null); }} /></div>;
  return <form className="login-card identity-card" onSubmit={verify} aria-busy={busy}>
    <div><span className="identity-eyebrow">SEGURANÇA DA CONTA</span><h2>{challenge.purpose === "ENROLL" ? "Configure seu autenticador" : "Verificação em duas etapas"}</h2></div>
    <p>O acesso será liberado após a verificação. Esta etapa expira em cinco minutos; atualizar a página exige novo login.</p>
    {expired && <p role="alert">Esta etapa expirou. Volte ao login para iniciar uma nova verificação.</p>}
    {challenge.purpose === "ENROLL" && !expired && <>
      {!uri && <button disabled={busy} className="btn-secondary" type="button" onClick={() => void provision()}>Preparar autenticador</button>}
      {uri && <MfaProvisioning uri={uri} />}
    </>}
    <label className="identity-field" htmlFor="mfa-code">{challenge.purpose === "LOGIN" ? "Código do autenticador ou de recuperação" : "Código do autenticador"}<input id="mfa-code" autoComplete="one-time-code" required minLength={6} maxLength={64} value={code} disabled={busy || expired} onChange={e => setCode(e.target.value)} /></label>
    {error && <p role="alert">{error}</p>}
    <button disabled={busy || expired || (challenge.purpose === "ENROLL" && !uri)} className="btn-primary" type="submit">{busy ? "Verificando…" : "Verificar e continuar"}</button>
    <button className="btn-secondary" disabled={busy} type="button" onClick={() => beginMfa?.(undefined)}>Voltar ao login</button>
    {challenge.purpose === "LOGIN" && <p>Perdeu o dispositivo? Use um código de recuperação. Sem os códigos, contate o suporte para o procedimento de recuperação assistida.</p>}
  </form>;
}
