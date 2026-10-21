import { useRef, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import {
  listDeliveryExceptions,
  registerDeliveryException,
  type DeliveryException,
  type DeliveryExceptionCode,
} from "../api/deliveryExceptionsApi";
import type { Delivery } from "../types";

const labels: Record<DeliveryExceptionCode, string> = {
  CUSTOMER_ABSENT: "Cliente ausente",
  REFUSED: "Entrega recusada",
  DAMAGED: "Avaria",
  OPERATIONAL_FAILURE: "Falha operacional",
  RESCHEDULED: "Reagendar tentativa",
  RESUMED: "Retomar tentativa",
};

const failures: DeliveryExceptionCode[] = [
  "CUSTOMER_ABSENT",
  "REFUSED",
  "DAMAGED",
  "OPERATIONAL_FAILURE",
];

function nextCodes(events: DeliveryException[]): DeliveryExceptionCode[] {
  const last = events.at(-1);
  if (!last || last.code === "RESUMED") return failures;
  if (last.code === "RESCHEDULED") return ["RESUMED"];
  return ["RESCHEDULED", "RESUMED"];
}

interface Props {
  readonly deliveries: Delivery[];
  readonly canOperate: boolean;
}

/** Only updates the attempt ledger; load plans and trip routes are unaffected. */
export function DeliveryExceptionsPanel({ deliveries, canOperate }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [deliveryId, setDeliveryId] = useState(deliveries[0]?.id ?? "");
  const [events, setEvents] = useState<DeliveryException[]>([]);
  const [loading, setLoading] = useState(false);
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [code, setCode] = useState<DeliveryExceptionCode>("CUSTOMER_ABSENT");
  const [reason, setReason] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const requestId = useRef<string | null>(null);

  const selected = deliveries.find((delivery) => delivery.id === deliveryId);
  const codes = nextCodes(events);
  const selectedCode = codes.includes(code) ? code : codes[0];
  const canWrite = canOperate && selected?.status !== "DELIVERED";

  async function refresh(id: string) {
    setLoading(true);
    setError("");
    try {
      setEvents(await listDeliveryExceptions(id));
    } catch {
      setError("Não foi possível carregar o histórico de ocorrências.");
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }

  function switchDelivery(id: string) {
    setDeliveryId(id);
    setEvents([]);
    setReason("");
    setScheduledFor("");
    setCode("CUSTOMER_ABSENT");
    setNotice("");
    requestId.current = null;
    void refresh(id);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!deliveryId || !canWrite || posting) return;
    const key = requestId.current ?? crypto.randomUUID();
    requestId.current = key;
    setPosting(true);
    setError("");
    setNotice("");
    try {
      const scheduled = selectedCode === "RESCHEDULED"
        ? new Date(scheduledFor).toISOString()
        : undefined;
      await registerDeliveryException(deliveryId, {
        code: selectedCode,
        reason: reason.trim(),
        idempotency_key: key,
        ...(scheduled ? { scheduled_for: scheduled } : {}),
      });
      requestId.current = null;
      setReason("");
      setScheduledFor("");
      setNotice("Ocorrência registrada no histórico da entrega.");
      await refresh(deliveryId);
    } catch {
      setError("Não foi possível registrar a ocorrência. Verifique a situação e tente novamente.");
    } finally {
      setPosting(false);
    }
  }

  return (
    <section aria-label="Exceções operacionais" className="entity-section">
      <h2>Ocorrências e novas tentativas</h2>
      <p className="entity-form-help">
        A ausência, recusa ou avaria fica registrada. Reagendar não altera
        automaticamente a rota nem libera o caminhão.
      </p>
      <button
        className="btn-secondary"
        type="button"
        aria-expanded={expanded}
        onClick={() => {
          setExpanded(!expanded);
          if (!expanded && deliveryId) void refresh(deliveryId);
        }}
      >
        {expanded ? "Ocultar ocorrências" : "Consultar ou registrar ocorrência"}
      </button>
      {expanded ? (
        <div>
          <label htmlFor="oc94-delivery">Entrega</label>
          <select
            id="oc94-delivery"
            value={deliveryId}
            disabled={posting}
            onChange={(event) => switchDelivery(event.target.value)}
          >
            {deliveries.map((delivery) => (
              <option key={delivery.id} value={delivery.id}>
                Parada {delivery.sequence} — {delivery.status}
              </option>
            ))}
          </select>
          {error ? <AlertBanner>{error}</AlertBanner> : null}
          {notice ? <p role="status">{notice}</p> : null}
          {loading ? <p role="status">Consultando ocorrências...</p> : null}
          {!loading && events.length === 0 && !error ? (
            <p>Não há ocorrências registradas para esta entrega.</p>
          ) : null}
          {!loading && events.length > 0 ? (
            <ol aria-label="Histórico das tentativas">
              {events.map((item) => (
                <li key={item.id}>
                  <strong>{labels[item.code]}</strong>
                  {" — "}
                  <time dateTime={item.created_at}>
                    {new Date(item.created_at).toLocaleString("pt-BR")}
                  </time>
                  <p>{item.reason}</p>
                  {item.scheduled_for ? (
                    <p>Nova tentativa: {new Date(item.scheduled_for).toLocaleString("pt-BR")}</p>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : null}
          {canWrite && !loading && !error ? (
            <form onSubmit={(event) => void submit(event)}>
              <label htmlFor="oc94-code">Ação</label>
              <select
                id="oc94-code"
                value={selectedCode}
                onChange={(event) => {
                  setCode(event.target.value as DeliveryExceptionCode);
                  requestId.current = null;
                }}
                disabled={posting}
              >
                {codes.map((value) => <option key={value} value={value}>{labels[value]}</option>)}
              </select>
              <label htmlFor="oc94-reason">Motivo (mínimo de 10 caracteres)</label>
              <textarea
                id="oc94-reason"
                required
                minLength={10}
                maxLength={1000}
                value={reason}
                disabled={posting}
                onChange={(event) => {
                  setReason(event.target.value);
                  requestId.current = null;
                }}
              />
              {selectedCode === "RESCHEDULED" ? (
                <>
                  <label htmlFor="oc94-schedule">Data e hora da nova tentativa</label>
                  <input
                    id="oc94-schedule"
                    type="datetime-local"
                    required
                    value={scheduledFor}
                    disabled={posting}
                    onChange={(event) => {
                      setScheduledFor(event.target.value);
                      requestId.current = null;
                    }}
                  />
                </>
              ) : null}
              <button
                className="btn-primary"
                type="submit"
                disabled={posting || reason.trim().length < 10 || (selectedCode === "RESCHEDULED" && !scheduledFor)}
              >
                {posting ? "Registrando..." : "Registrar no histórico"}
              </button>
            </form>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
