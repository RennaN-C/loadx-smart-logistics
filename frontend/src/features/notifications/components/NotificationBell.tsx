import { useEffect, useId, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Icon } from "../../../components/Icon";
import { AlertBanner } from "../../../components/AlertBanner";
import { getNotificationSource, listNotifications, markNotificationRead, type NotificationItem, type NotificationPage } from "../api/notificationsApi";
import { useNotificationCounter } from "../hooks/NotificationContext";
import { NotificationList } from "./NotificationList";
import "../notifications.css";

export function NotificationBell() {
  const counter = useNotificationCounter();
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState<NotificationPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0);
  const wrapper = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const id = useId();
  const navigate = useNavigate();
  const location = useLocation();
  async function load() {
    const request = ++sequence.current;
    setLoading(true); setError("");
    try {
      const result = await listNotifications({ page_size: 5 });
      if (request === sequence.current) { setPage(result); counter.synchronize(result.unreadCount); }
    } catch {
      if (request === sequence.current) { setPage(null); setError("Não foi possível carregar suas notificações."); }
    } finally { if (request === sequence.current) setLoading(false); }
  }
  useEffect(() => { setOpen(false); sequence.current += 1; }, [location.pathname, location.search]);
  useEffect(() => {
    if (!open) return;
    heading.current?.focus();
    const dismiss = (event: MouseEvent) => { if (!wrapper.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); setOpen(false); trigger.current?.focus(); }
    };
    document.addEventListener("mousedown", dismiss);
    document.addEventListener("keydown", escape);
    return () => { sequence.current += 1; document.removeEventListener("mousedown", dismiss); document.removeEventListener("keydown", escape); };
  }, [open]);
  function toggle() { if (!open) { setPage(null); void load(); } setOpen(!open); }
  async function act(item: NotificationItem, navigateToSource: boolean) {
    setBusy(true); setError("");
    if (!navigateToSource) heading.current?.focus();
    try {
      // Revalidate the actual source before navigation; a notification is not a permission grant.
      const href = navigateToSource ? await getNotificationSource(item.id) : null;
      if (!item.read_at) await markNotificationRead(item.id);
      await load();
      if (href) { setOpen(false); navigate(href); }
    } catch { setError("A ação não foi concluída. Verifique seu acesso e tente novamente."); }
    finally { setBusy(false); }
  }
  let label = "Notificações";
  if (counter.failed) label = "Notificações, contador indisponível";
  else if (counter.count !== null) label = `Notificações, ${counter.count} não lidas`;
  return <div ref={wrapper} className="notification-bell" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <button ref={trigger} type="button" className="notification-bell-trigger" aria-label={label} title="Notificações" aria-expanded={open} aria-controls={`${id}-panel`} onClick={toggle}>
      <Icon name="bell" size={22} />
      {counter.failed && <span className="notification-counter-error" aria-hidden="true">!</span>}
      {!counter.failed && counter.count !== null && counter.count > 0 && <span className="notification-count" aria-hidden="true">{counter.count > 99 ? "99+" : counter.count}</span>}
    </button>
    {open && <section id={`${id}-panel`} className="notification-dropdown" aria-labelledby={`${id}-heading`} aria-busy={loading || busy}>
      <header className="notification-dropdown-header"><div><span className="notification-kicker">Sua caixa</span><h2 id={`${id}-heading`} ref={heading} tabIndex={-1}>Notificações</h2></div><button type="button" className="notification-text-button" onClick={() => { setOpen(false); trigger.current?.focus(); }} aria-label="Fechar notificações">Fechar</button></header>
      {error && <div className="notification-dropdown-feedback"><AlertBanner>{error}</AlertBanner><button type="button" className="btn-secondary" disabled={loading || busy} onClick={() => void load()}>Tentar novamente</button></div>}
      {loading && <output className="notification-feedback">Buscando atualizações…</output>}
      {!loading && page && (page.items.length ? <NotificationList compact items={page.items} busy={busy} onRead={(item) => void act(item, false)} onOpen={(item) => void act(item, true)} /> : <div className="notification-empty"><Icon name="bell" size={26} /><h3>Tudo em dia</h3><p>Você ainda não tem notificações recebidas.</p></div>)}
      <footer className="notification-dropdown-footer"><Link to="/notifications" onClick={() => setOpen(false)}>Abrir central de notificações <Icon name="arrow-right" size={16} /></Link></footer>
    </section>}
  </div>;
}
