import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertBanner } from "../../../components/AlertBanner";
import { Icon } from "../../../components/Icon";
import { getNotificationPreferences, saveNotificationPreferences, type NotificationCategory, type NotificationPreference } from "../api/notificationsApi";
import "../notifications.css";

const DESCRIPTIONS: Record<NotificationCategory, { title: string; description: string }> = {
  TRIPS: { title: "Viagens", description: "Início de viagens da sua operação." },
  OCCURRENCES: { title: "Ocorrências", description: "Novas ocorrências registradas nas viagens disponíveis para sua conta." },
  SECURITY: { title: "Segurança", description: "Avisos obrigatórios não podem ser desativados. Novos alertas dependem das funções de segurança disponíveis." },
};
export function NotificationPreferences() {
  const [saved, setSaved] = useState<NotificationPreference[] | null>(null);
  const [draft, setDraft] = useState<NotificationPreference[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const items = await getNotificationPreferences(); setSaved(items); setDraft(items); }
    catch { setSaved(null); setError("Não foi possível consultar suas preferências de notificações."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const changed = saved !== null && draft.some((item) => item.enabled !== saved.find((value) => value.category === item.category)?.enabled);
  async function save() {
    setBusy(true); setError(""); setNotice("");
    try { const items = await saveNotificationPreferences(draft); setSaved(items); setDraft(items); setNotice("Preferências de notificações salvas."); }
    catch { setError("Não foi possível salvar. Suas alterações foram mantidas para tentar novamente."); }
    finally { setBusy(false); }
  }
  return <section id="notification-preferences" className="account-section notification-preferences" aria-labelledby="notification-preferences-heading" aria-busy={loading || busy}>
    <div className="notification-preferences-header"><div><h2 id="notification-preferences-heading">Notificações</h2><p>Escolha quais atualizações deseja receber na sua central.</p></div><Link to="/notifications">Abrir central <Icon name="arrow-right" size={16} /></Link></div>
    {error && <AlertBanner>{error}</AlertBanner>}
    {notice && <p role="status" className="notification-success">{notice}</p>}
    {loading ? <p role="status">Consultando preferências…</p> : saved ? <form onSubmit={(event) => { event.preventDefault(); void save(); }}>
      <fieldset disabled={busy} className="notification-preference-options"><legend className="sr-only">Categorias de notificações</legend>{draft.map((item) => <label className="notification-preference" key={item.category}>
        <span><strong>{DESCRIPTIONS[item.category].title}{item.mandatory && <span className="notification-mandatory">Obrigatória</span>}</strong><small id={`notification-help-${item.category}`}>{DESCRIPTIONS[item.category].description}</small></span>
        <input type="checkbox" checked={item.enabled} disabled={item.mandatory} aria-label={DESCRIPTIONS[item.category].title} aria-describedby={`notification-help-${item.category}`} onChange={(event) => { setNotice(""); setDraft((current) => current.map((value) => value.category === item.category ? { ...value, enabled: event.target.checked } : value)); }} />
      </label>)}</fieldset>
      <p className="notification-footnote">A escolha vale para novas notificações. As já recebidas permanecem na sua caixa.</p>
      <div className="account-actions"><button className="btn-primary" type="submit" disabled={busy || !changed}>{busy ? "Salvando…" : "Salvar preferências"}</button><button className="btn-secondary" type="button" disabled={busy || !changed} onClick={() => { setDraft(saved); setNotice(""); setError(""); }}>Cancelar</button></div>
    </form> : <button type="button" className="btn-secondary" onClick={() => void load()}>Tentar novamente</button>}
  </section>;
}
