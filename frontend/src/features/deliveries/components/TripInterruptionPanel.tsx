import { useEffect, useRef, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import {
  changeTripInterruption,
  listTripInterruptions,
  type TripInterruptionEvent,
} from "../api/tripInterruptionApi";
import type { Trip } from "../types";

interface Props {
  readonly trip: Trip;
  readonly onChanged: () => Promise<void>;
}

/** Explicit manager action; the server owns locking and the status transition. */
export function TripInterruptionPanel({ trip, onChanged }: Props) {
  const [entries, setEntries] = useState<TripInterruptionEvent[]>([]);
  const [reason, setReason] = useState("");
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const key = useRef<string | null>(null);
  const eligible = trip.status === "IN_ROUTE" || trip.status === "INTERRUPTED";
  const action = trip.status === "INTERRUPTED" ? "RESUMED" : "INTERRUPTED";

  useEffect(() => {
    let active = true;
    void listTripInterruptions(trip.id)
      .then((items) => {
        if (active) setEntries(items);
      })
      .catch(() => {
        if (active) setError("Não foi possível consultar as interrupções.");
      });
    return () => {
      active = false;
    };
  }, [trip.id, trip.status]);

  async function confirm() {
    if (!eligible || busy || reason.trim().length < 8) return;
    setBusy(true);
    setError("");
    if (!key.current) key.current = crypto.randomUUID();
    try {
      await changeTripInterruption(trip.id, action, reason.trim(), key.current);
      setReason("");
      setOpen(false);
      key.current = null;
      await onChanged();
    } catch {
      setError("Operação não confirmada. Verifique o estado atual antes de tentar novamente.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="entity-section" aria-label="Interrupção e retomada da viagem">
      <h2>Interrupção e retomada</h2>
      <p className="entity-form-help">
        Uma viagem interrompida mantém motorista, caminhão, pedidos e carga
        reservados. Nenhuma entrega poderá avançar até a retomada.
      </p>
      {error ? <AlertBanner>{error}</AlertBanner> : null}
      {eligible ? (
        open ? (
          <div className="entity-form">
            <label htmlFor="trip-interruption-reason">
              Motivo obrigatório da {action === "INTERRUPTED" ? "interrupção" : "retomada"}
            </label>
            <textarea
              id="trip-interruption-reason"
              value={reason}
              maxLength={500}
              rows={3}
              disabled={busy}
              onChange={(event) => {
                setReason(event.target.value);
                key.current = null;
              }}
            />
            <div className="entity-toolbar">
              <button type="button" className="btn-secondary" disabled={busy}
                onClick={() => setOpen(false)}>Voltar</button>
              <button type="button" className="btn-primary"
                disabled={busy || reason.trim().length < 8}
                onClick={() => void confirm()}>
                {busy ? "Registrando..." : action === "INTERRUPTED" ? "Confirmar interrupção" : "Confirmar retomada"}
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="btn-secondary"
            onClick={() => setOpen(true)}>
            {action === "INTERRUPTED" ? "Interromper viagem" : "Retomar viagem"}
          </button>
        )
      ) : null}
      {entries.length > 0 ? (
        <div>
          <h3>Histórico de interrupções</h3>
          <ul>
            {entries.map((entry) => (
              <li key={entry.id}>
                {entry.action === "INTERRUPTED" ? "Interrompida" : "Retomada"}
                {" — "}{entry.reason}
                {" — "}{new Date(entry.created_at).toLocaleString("pt-BR")}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
