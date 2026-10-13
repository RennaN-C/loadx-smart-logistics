import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { BrandPanel } from "../components/BrandPanel";
import { requestRecovery, confirmRecovery } from "../api/identityApi";
import { accountError } from "../components/accountError";
import "./LoginPage.css";
import "./Identity.css";

export function PasswordRecoveryPage({ reset = false }: { readonly reset?: boolean }) {
  const { updateUser } = useAuth();
  const [token, setToken] = useState(() => {
    if (!reset) return "";
    const value = new URLSearchParams(globalThis.location.hash.slice(1)).get("token") ?? "";
    return value;
  });
  useEffect(() => { if (reset) globalThis.history.replaceState(globalThis.history.state, "", globalThis.location.pathname + globalThis.location.search); }, [reset]);
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [done, setDone] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    if (reset && password !== confirmation) { setError("As senhas devem ser iguais."); return; }
    setBusy(true);
    try { if (reset) { await confirmRecovery(token, password); updateUser(null, "password-changed"); } else await requestRecovery(email); setPassword(""); setConfirmation(""); setToken(""); setDone(true); }
    catch (e) { setError(accountError(e)); } finally { setBusy(false); }
  }
  return <div className="login-page"><BrandPanel /><main className="login-formside"><form className="login-card identity-card" onSubmit={submit} aria-busy={busy}><div><span className="identity-eyebrow">RECUPERAÇÃO DE ACESSO</span><h2>{reset ? "Defina uma nova senha" : "Esqueceu sua senha?"}</h2></div>
    {done ? <output>{reset ? "Senha redefinida. Todas as sessões foram encerradas. Entre novamente; a verificação MFA permanece ativa." : "Se a conta for elegível, você receberá instruções de recuperação. Confira sua caixa de entrada."}</output> : <><p>{reset ? "Use de 15 a 128 caracteres. Sua senha não será enviada por e-mail." : "Informe seu e-mail de acesso para solicitar um link temporário."}</p>
    {reset ? <>{!token && <p role="alert">Link ausente. Solicite uma nova recuperação.</p>}<label className="identity-field" htmlFor="reset-password">Nova senha<input id="reset-password" type="password" autoComplete="new-password" required minLength={15} maxLength={128} value={password} disabled={busy} onChange={e => setPassword(e.target.value)} /></label><label className="identity-field" htmlFor="reset-confirm">Confirmar nova senha<input id="reset-confirm" type="password" autoComplete="new-password" required minLength={15} maxLength={128} value={confirmation} disabled={busy} onChange={e => setConfirmation(e.target.value)} /></label></> : <label className="identity-field" htmlFor="recovery-email">E-mail<input id="recovery-email" type="email" autoComplete="email" required maxLength={255} value={email} disabled={busy} onChange={e => setEmail(e.target.value)} /></label>}
    {error && <p role="alert">{error}</p>}<button disabled={busy || (reset && !token)} className="btn-primary" type="submit">{busy ? "Aguarde…" : (reset ? "Redefinir senha" : "Solicitar recuperação")}</button></>}
    <Link className="login-recovery-link" to="/login">Voltar ao login</Link>{!done && reset && <Link className="login-recovery-link" to="/password-recovery">Solicitar novo link</Link>}
  </form></main></div>;
}
