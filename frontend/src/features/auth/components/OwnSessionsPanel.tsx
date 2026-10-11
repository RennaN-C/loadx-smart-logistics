import { useEffect, useState } from "react";
import { listOwnSessions, revokeOtherSessions, revokeOwnSession, type OwnSession } from "../api/accountApi";
import { accountError } from "./accountError";
export function OwnSessionsPanel({ onSignedOut }: { readonly onSignedOut: (notice: "session-revoked") => void }) {
  const [sessions, setSessions] = useState<OwnSession[]>([]); const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState<string | null>(null); const [confirm, setConfirm] = useState<OwnSession | "others" | null>(null); const [success, setSuccess] = useState(false);
  useEffect(() => {
    let active = true; setLoading(true); setError(null);
    listOwnSessions().then((rows) => { if (active) { setSessions(rows); setLoaded(true); } }).catch((error_: unknown) => { if (active) setError(accountError(error_)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refresh]);
  async function revoke() {
    if (!confirm || busy) { return; }
    setBusy(true); setError(null); setSuccess(false);
    try {
      if (confirm === "others") await revokeOtherSessions(); else await revokeOwnSession(confirm.id);
      if (confirm !== "others" && confirm.current) { onSignedOut("session-revoked"); return; }
      setConfirm(null); setSuccess(true); setRefresh((value) => value + 1);
    } catch (error_) { setError(accountError(error_)); } finally { setBusy(false); }
  }
  return <div className="account-sessions" aria-busy={loading || busy}>
    <p>Sessões ativas da sua conta. A identificação de dispositivo e localização não está disponível. Cada sessão expira após 30 minutos sem atividade ou, no máximo, 8 horas desde o login.</p>
    <button type="button" className="btn-secondary" disabled={loading || busy} onClick={() => setRefresh((value) => value + 1)}>Atualizar sessões</button>
    {loading && <output>Carregando sessões…</output>}{error && <p role="alert">{error}</p>}{error && loaded && <p>A lista anterior pode estar desatualizada. Atualize para confirmar o estado.</p>}{success && <output>Sessões selecionadas encerradas.</output>}
    {loaded && !loading && sessions.length === 0 && <p>Nenhuma sessão ativa foi encontrada.</p>}
    <ul className="account-session-list">{sessions.map((session) => <li key={session.id}>
      <h3>{session.current ? "Sessão atual" : "Outra sessão"}</h3>
      <dl>{([{ label: "Início", value: session.created_at }, { label: "Última atividade", value: session.last_seen_at }, { label: "Limite por inatividade", value: session.idle_expires_at }, { label: "Limite absoluto", value: session.absolute_expires_at }]).map((item) => <div key={item.label}><dt>{item.label}</dt><dd><time dateTime={item.value}>{new Date(item.value).toLocaleString("pt-BR")}</time></dd></div>)}</dl>
      <button type="button" className="btn-secondary" disabled={loading || busy} onClick={() => setConfirm(session)}>{session.current ? "Encerrar sessão atual" : "Encerrar esta sessão"}</button>
    </li>)}</ul>
    {sessions.some((session) => !session.current) && <button type="button" className="btn-secondary" disabled={loading || busy} onClick={() => setConfirm("others")}>Encerrar outras sessões</button>}
    {confirm && <fieldset className="account-confirm"><legend>Confirmar encerramento</legend>
      <p>{confirm === "others" ? "Encerrar todas as outras sessões? A atual será mantida." : "Encerrar a sessão selecionada? Se for a atual, será necessário entrar novamente."}</p>
      <div className="account-actions"><button type="button" className="btn-primary" disabled={busy} onClick={() => void revoke()}>Confirmar encerramento</button><button type="button" className="btn-secondary" disabled={busy} onClick={() => setConfirm(null)}>Cancelar encerramento</button></div>
    </fieldset>}
  </div>;
}
