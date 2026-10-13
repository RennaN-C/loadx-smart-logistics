import { useEffect, useState, type FormEvent } from "react";
import { disableMfa, enrollMfa, getMfaStatus, regenerateCodes, type MfaStatus } from "../api/identityApi";
import { useAuth } from "../hooks/useAuth";
import { accountError } from "./accountError";
import { RecoveryCodes } from "./RecoveryCodes";
import "../pages/Identity.css";

export function OwnMfaPanel() {
  const { updateUser, beginMfa } = useAuth();
  const [status, setStatus] = useState<MfaStatus | null>(null); const [loading, setLoading] = useState(true);
  const [password, setPassword] = useState(""); const [code, setCode] = useState(""); const [action, setAction] = useState("regenerate");
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [codes, setCodes] = useState<string[]>([]);
  async function load() { setLoading(true); setError(""); try { setStatus(await getMfaStatus()); } catch (e) { setError(accountError(e)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      if (!status?.enabled) { const challenge = await enrollMfa(password); beginMfa?.(challenge); }
      else if (action === "regenerate") setCodes(await regenerateCodes(password, code));
      else { await disableMfa(password, code); updateUser(null, "session-revoked"); }
      setPassword(""); setCode("");
    } catch (e) { setError(accountError(e)); } finally { setBusy(false); }
  }
  if (loading) return <output>Consultando verificação em duas etapas…</output>;
  if (!status) return <div><p role="alert">{error}</p><button className="btn-secondary" onClick={() => void load()}>Tentar novamente</button></div>;
  if (codes.length) return <RecoveryCodes codes={codes} onDone={() => setCodes([])} />;
  return <form className="account-form identity-management" onSubmit={submit} aria-label="Autenticação multifator" aria-busy={busy}><header><h3>Verificação em duas etapas</h3><span className={`identity-status ${status.enabled ? "is-enabled" : ""}`}>{status.enabled ? "Ativa" : "Não configurada"}</span></header><p>{status.required ? "Obrigatória para seu perfil. Trocar o autenticador encerra as sessões e exige nova configuração antes de liberar o acesso." : "Proteja sua conta com um aplicativo autenticador."}</p>
    {status.enabled && <label className="identity-field" htmlFor="mfa-action">Ação<select id="mfa-action" value={action} disabled={busy} onChange={e => setAction(e.target.value)}><option value="regenerate">Regenerar códigos de recuperação</option><option value="disable">{status.required ? "Trocar autenticador e encerrar sessões" : "Desativar e encerrar sessões"}</option></select></label>}
    <div className="account-fields"><label className="identity-field" htmlFor="mfa-password">Senha atual<input id="mfa-password" type="password" autoComplete="current-password" required maxLength={128} value={password} disabled={busy} onChange={e => setPassword(e.target.value)} /></label>{status.enabled && <label className="identity-field" htmlFor="mfa-management-code">Código do autenticador ou recuperação<input id="mfa-management-code" autoComplete="one-time-code" required minLength={6} maxLength={64} value={code} disabled={busy} onChange={e => setCode(e.target.value)} /></label>}</div>
    {error && <p role="alert">{error}</p>}<button className="btn-primary" disabled={busy} type="submit">{busy ? "Validando…" : (status.enabled ? "Confirmar ação de segurança" : "Configurar autenticador")}</button>
  </form>;
}
