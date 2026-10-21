import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertBanner } from "../../../components/AlertBanner";
import { Icon } from "../../../components/Icon";
import { Pagination } from "../../../components/Pagination";
import { getNotificationSource, listNotifications, markAllNotificationsRead, markNotificationRead, type NotificationCategory, type NotificationItem, type NotificationPage } from "../api/notificationsApi";
import { NotificationList } from "../components/NotificationList";
import { useNotificationCounter } from "../hooks/NotificationContext";
import "../notifications.css";

function parseFilters(params: URLSearchParams) {
  const value = params.get("category");
  const category: NotificationCategory | undefined = value === "TRIPS" || value === "OCCURRENCES" || value === "SECURITY" ? value : undefined;
  let read: boolean | undefined;
  if (params.get("read") === "true") read = true;
  if (params.get("read") === "false") read = false;
  const sortOrder = params.get("sort_order") === "asc" ? "asc" as const : "desc" as const;
  const page = Math.max(1, Math.min(1_000_000, Math.floor(Number(params.get("page")) || 1)));
  return { category, read, sortOrder, page };
}

export function NotificationsPage() {
  const [params, setParams] = useSearchParams();
  const { category, read, sortOrder, page } = parseFilters(params);
  const [result, setResult] = useState<NotificationPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const sequence = useRef(0);
  const feedback = useRef<HTMLOutputElement>(null);
  useEffect(() => { if (notice) feedback.current?.focus(); }, [notice]);
  const { count, synchronize } = useNotificationCounter();
  const navigate = useNavigate();
  const load = useCallback(async () => {
    const request = ++sequence.current;
    setLoading(true); setError("");
    try {
      const data = await listNotifications({ page, page_size: 20, sort_order: sortOrder, category, read });
      if (request === sequence.current) { setResult(data); synchronize(data.unreadCount); }
    } catch {
      if (request === sequence.current) { setResult(null); setError("Não foi possível carregar a central. Tente novamente."); }
    } finally { if (request === sequence.current) setLoading(false); }
  }, [page, sortOrder, category, read, synchronize]);
  useEffect(() => { void load(); return () => { sequence.current += 1; }; }, [load]);
  useEffect(() => {
    if (result && count !== null && count !== result.unreadCount && !loading && !busy) void load();
  }, [count, result, loading, busy, load]);
  function filter(name: string, value: string) {
    setNotice("");
    setParams((current) => { const next = new URLSearchParams(current); next.delete("page"); if (value) { next.set(name, value); } else { next.delete(name); } return next; });
  }
  async function act(item: NotificationItem | null, openSource = false) {
    setBusy(true); setError(""); setNotice("");
    try {
      const href = item && openSource ? await getNotificationSource(item.id) : null;
      if (item) { if (!item.read_at) await markNotificationRead(item.id); }
      else await markAllNotificationsRead();
      await load();
      if (href) navigate(href);
      else setNotice(item ? "Notificação marcada como lida." : "Todas as notificações disponíveis foram marcadas como lidas.");
    } catch { setError("Não foi possível concluir a ação. Seu acesso pode ter mudado; atualize e tente novamente."); }
    finally { setBusy(false); }
  }
  return <div className="entity-page notifications-page">
    <header className="entity-header"><div><span className="notification-kicker">Comunicação operacional</span><h1>Central de notificações</h1><p className="entity-lede">Acompanhe as atualizações destinadas à sua conta e continue a operação.</p></div><Link className="entity-header-link" to="/account#notification-preferences"><Icon name="settings" size={17} /> Preferências</Link></header>
    <section className="notification-workspace" aria-labelledby="notification-inbox-heading" aria-busy={loading || busy}>
      <header className="notification-workspace-header"><div><h2 id="notification-inbox-heading">Sua caixa de entrada</h2><p>{result ? <><strong>{result.unreadCount}</strong> {result.unreadCount === 1 ? "não lida" : "não lidas"} <span aria-hidden="true">·</span> {result.total} {result.total === 1 ? "resultado" : "resultados"}</> : "Somente notificações disponíveis para sua conta."}</p></div><div className="notification-toolbar-actions"><button type="button" className="btn-secondary" disabled={loading || busy} onClick={() => void load()}>Atualizar</button><button type="button" className="btn-primary" disabled={loading || busy || !result?.unreadCount} onClick={() => void act(null)}>Marcar todas como lidas</button></div></header>
      <div className="notification-filters">
        <label>Situação<select value={read === undefined ? "" : String(read)} disabled={busy} onChange={(event) => filter("read", event.target.value)}><option value="">Todas</option><option value="false">Não lidas</option><option value="true">Lidas</option></select></label>
        <label>Categoria<select value={category ?? ""} disabled={busy} onChange={(event) => filter("category", event.target.value)}><option value="">Todas</option><option value="TRIPS">Viagens</option><option value="OCCURRENCES">Ocorrências</option><option value="SECURITY">Segurança</option></select></label>
        <label>Ordenação<select value={sortOrder} disabled={busy} onChange={(event) => filter("sort_order", event.target.value)}><option value="desc">Mais recentes primeiro</option><option value="asc">Mais antigas primeiro</option></select></label>
      </div>
      {notice && <output ref={feedback} tabIndex={-1} className="notification-success">{notice}</output>}
      {error && <div className="notification-feedback"><AlertBanner>{error}</AlertBanner><button type="button" className="btn-secondary" disabled={loading || busy} onClick={() => void load()}>Tentar novamente</button></div>}
      {loading && <output className="notification-feedback">Carregando suas notificações…</output>}
      {!loading && result && (result.items.length ? <NotificationList items={result.items} busy={busy} onRead={(item) => void act(item)} onOpen={(item) => void act(item, true)} /> : <div className="notification-empty"><span className="notification-empty-icon"><Icon name="bell" size={30} /></span><h3>{read === false ? "Nenhuma notificação não lida" : "Nenhuma notificação por aqui"}</h3><p>{category || read !== undefined ? "Ajuste os filtros para consultar outras atualizações." : "As atualizações da sua operação aparecerão aqui quando forem recebidas."}</p></div>)}
      {result && !loading && <Pagination page={result.page} totalPages={result.totalPages} onChange={(value) => setParams((current) => { const next = new URLSearchParams(current); next.set("page", String(value)); return next; })} label="notificações" />}
    </section>
    <p className="notification-footnote">Sua leitura é pessoal. A central preserva o histórico e verifica seu acesso à operação ao abrir cada atualização.</p>
  </div>;
}
