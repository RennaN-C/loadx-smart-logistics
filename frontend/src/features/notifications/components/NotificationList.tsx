import { Icon } from "../../../components/Icon";
import type { NotificationItem } from "../api/notificationsApi";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });
interface Props {
  readonly items: readonly NotificationItem[];
  readonly busy: boolean;
  readonly compact?: boolean;
  readonly onRead: (item: NotificationItem) => void;
  readonly onOpen: (item: NotificationItem) => void;
}
export function NotificationList({ items, busy, compact = false, onRead, onOpen }: Props) {
  return <ul className={`notification-list${compact ? " notification-list--compact" : ""}`} aria-label="Notificações recebidas">
    {items.map((item) => <li key={item.id} className="notification-item" data-unread={item.read_at === null}>
      <span className="notification-item-icon"><Icon name={item.category === "TRIPS" ? "truck" : "report"} size={21} /></span>
      <div className="notification-item-content">
        <div className="notification-item-heading"><h3>{item.title}</h3><span className={`notification-state${item.read_at ? "" : " notification-state--unread"}`}>{item.read_at ? "Lida" : "Não lida"}</span></div>
        <p>{item.summary}</p>
        <div className="notification-item-meta"><span>{item.category === "TRIPS" ? "Viagens" : "Ocorrências"}</span><time dateTime={item.created_at}>{dateTime.format(new Date(item.created_at))}</time></div>
        <div className="notification-item-actions">
          <button type="button" className="notification-text-button" disabled={busy} onClick={() => onOpen(item)} aria-label={`Abrir operação: ${item.title}`}>
            Abrir operação <Icon name="arrow-right" size={15} />
          </button>
          {!item.read_at && <button type="button" className="notification-text-button notification-read-action" disabled={busy} onClick={() => onRead(item)} aria-label={`Marcar como lida: ${item.title}`}>Marcar como lida</button>}
        </div>
      </div>
    </li>)}
  </ul>;
}
