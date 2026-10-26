import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Tabs } from "../../../components/Tabs";
import {
  agendaKinds, fetchAgenda, type AgendaItem, type AgendaKind,
} from "../api/agendaApi";
import "./AgendaPage.css";

const dayMs = 86_400_000;
const labels: Record<AgendaKind, string> = {
  TRIP_CREATED: "Viagem criada", TRIP_STARTED: "Viagem iniciada",
  TRIP_FINISHED: "Viagem finalizada", LOADING_STARTED: "Carregamento iniciado",
  LOADING_FINISHED: "Carregamento concluído", DELIVERY_COMPLETED: "Entrega concluída",
  DELIVERY_EXCEPTION: "Exceção registrada", TRIP_CANCELED: "Viagem cancelada",
  TRIP_INTERRUPTED: "Viagem interrompida", TRIP_RESUMED: "Viagem retomada",
};
const fmtDate = new Intl.DateTimeFormat("pt-BR", { dateStyle: "full", timeZone: "UTC" });
const fmtTime = new Intl.DateTimeFormat("pt-BR", { timeStyle: "short", timeZone: "UTC" });
const weekday = new Intl.DateTimeFormat("pt-BR", { weekday: "short", timeZone: "UTC" });
const VIEW_TABS = [{ id: "calendar", label: "Calendário" }, { id: "list", label: "Lista de eventos" }] as const;

function dateShift(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00.000Z`);
  return new Date(date.getTime() + days * dayMs).toISOString().slice(0, 10);
}
function today(): string { return new Date().toISOString().slice(0, 10); }

export function AgendaPage() {
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [day, setDay] = useState(today);
  const [mode, setMode] = useState<"day" | "week">("week");
  const [kind, setKind] = useState<AgendaKind | "">("");
  const [truck, setTruck] = useState("");
  const [driver, setDriver] = useState("");
  const [state, setState] = useState<"loading" | "error" | "ready">("loading");
  const [items, setItems] = useState<AgendaItem[]>([]);
  const [reason, setReason] = useState("");
  const [attempt, setAttempt] = useState(0);
  const start = `${day}T00:00:00.000Z`;
  const end = `${dateShift(day, mode === "week" ? 7 : 1)}T00:00:00.000Z`;

  useEffect(() => {
    let active = true;
    setState("loading");
    setReason("");
    fetchAgenda({
      start, end,
      ...(kind ? { kind } : {}),
      ...(truck.trim() ? { truck_id: truck.trim() } : {}),
      ...(driver.trim() ? { driver_id: driver.trim() } : {}),
    }).then((data) => {
      if (active) { setItems(data.items); setState("ready"); }
    }).catch(() => {
      if (active) {
        setItems([]);
        setState("error");
        setReason("Não foi possível consultar a agenda. Confira o período, os filtros e suas permissões.");
      }
    });
    return () => { active = false; };
  }, [start, end, kind, truck, driver, attempt]);

  const groups = useMemo(() => {
    const result = new Map<string, AgendaItem[]>();
    for (const event of items) {
      const key = event.occurred_at.slice(0, 10);
      result.set(key, [...(result.get(key) ?? []), event]);
    }
    return [...result.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [items]);

  return <div className="entity-page agenda-page">
    <header className="entity-header">
      <div>
        <h1>Agenda operacional</h1>
        <p className="entity-lede">Atividades reais de viagens, carregamentos, entregas e ocorrências registradas.</p>
      </div>
    </header>
    <Tabs items={VIEW_TABS} active={view} onChange={setView} label="Exibição da agenda" />
    <p className="entity-form-help">Calendário de eventos históricos, não de horários previstos de entrega. Datas e horários exibidos em UTC.</p>
    <div className="agenda-controls" role="group" aria-label="Navegar pela agenda">
      <button type="button" className="btn-secondary" onClick={() => setDay(dateShift(day, mode === "week" ? -7 : -1))}>Anterior</button>
      <button type="button" className="btn-secondary" onClick={() => setDay(today())}>Hoje</button>
      <button type="button" className="btn-secondary" onClick={() => setDay(dateShift(day, mode === "week" ? 7 : 1))}>Próximo</button>
      <label>Visualização <select value={mode} onChange={e => setMode(e.target.value as "day" | "week")}><option value="day">Dia</option><option value="week">Semana</option></select></label>
      <label>Data inicial <input type="date" value={day} onChange={e => { if (e.target.value) setDay(e.target.value); }} /></label>
    </div>
    <div className="agenda-controls">
      <label>Tipo de evento <select value={kind} onChange={e => setKind(e.target.value as AgendaKind | "")}><option value="">Todos</option>{agendaKinds.map(k => <option key={k} value={k}>{labels[k]}</option>)}</select></label>
      <label>Caminhão (UUID opcional) <input value={truck} maxLength={36} placeholder="Todos" onChange={e => setTruck(e.target.value)} /></label>
      <label>Motorista (UUID opcional) <input value={driver} maxLength={36} placeholder="Todos" onChange={e => setDriver(e.target.value)} /></label>
    </div>
    {state === "loading" && <p role="status">Carregando eventos…</p>}
    {state === "error" && <><AlertBanner>{reason}</AlertBanner><button type="button" className="btn-secondary" onClick={() => setAttempt(n => n + 1)}>Tentar novamente</button></>}
    {state === "ready" && items.length === 0 && <p className="entity-state">Nenhuma atividade registrada neste período.</p>}
    {state === "ready" && <p className="entity-summary">{items.length} evento(s) registrados no período consultado.</p>}
    {state === "ready" && view === "calendar" && <div role="tabpanel" id="panel-calendar" aria-labelledby="tab-calendar" className="agenda-calendar" data-mode={mode}>
      {Array.from({ length: mode === "week" ? 7 : 1 }, (_, index) => dateShift(day, index)).map((date) => {
        const events = groups.find(([key]) => key === date)?.[1] ?? [];
        return <section className="agenda-calendar-day" key={date} data-today={date === today()}>
          <h2><span>{weekday.format(new Date(`${date}T00:00:00Z`))}</span><time dateTime={date}>{date.slice(8, 10)}/{date.slice(5, 7)}</time></h2>
          {events.length ? <ol>{events.map((event) => <li key={`${event.kind}-${event.resource_id}`}>
            <time dateTime={event.occurred_at}>{fmtTime.format(new Date(event.occurred_at))}</time>
            <strong>{labels[event.kind]}</strong><Link to={`/trips/${event.trip_id}`}>Abrir viagem</Link>
          </li>)}</ol> : <p>Sem eventos</p>}
        </section>;
      })}
    </div>}
    {state === "ready" && view === "list" && <div className="agenda-days" role="tabpanel" id="panel-list" aria-labelledby="tab-list">
      {groups.map(([date, events]) => <section className="agenda-day" key={date}>
        <h2>{fmtDate.format(new Date(`${date}T00:00:00Z`))}</h2>
        <ol>{events.map(e => <li key={`${e.kind}-${e.resource_id}`}>
          <time dateTime={e.occurred_at}>{fmtTime.format(new Date(e.occurred_at))}</time>
          <span>{labels[e.kind]}</span>
          <Link to={`/trips/${e.trip_id}`}>Abrir viagem</Link>
        </li>)}</ol>
      </section>)}
    </div>}
  </div>;
}
