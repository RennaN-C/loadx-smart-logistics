import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import {
  downloadManagementReport,
  fetchManagementSummary,
  type ManagementFilters,
  type ManagementSummary,
} from "../api/managementReportsApi";

const dayMs = 86_400_000;
function utcDate(offsetDays = 0): string {
  return new Date(Date.now() + offsetDays * dayMs).toISOString().slice(0, 10);
}
function makeFilters(start: string, end: string, truck: string, driver: string): ManagementFilters {
  const from = new Date(`${start}T00:00:00.000Z`);
  const until = new Date(new Date(`${end}T00:00:00.000Z`).getTime() + dayMs);
  if (!Number.isFinite(from.getTime()) || !Number.isFinite(until.getTime())
      || until <= from || until.getTime() - from.getTime() > 93 * dayMs) {
    throw new Error("Selecione um período válido de até 93 dias.");
  }
  return {
    start: from.toISOString(),
    end: until.toISOString(),
    ...(truck.trim() ? { truck_id: truck.trim() } : {}),
    ...(driver.trim() ? { driver_id: driver.trim() } : {}),
  };
}

const metrics: { key: keyof ManagementSummary; title: string }[] = [
  { key: "trips_created", title: "Viagens criadas" },
  { key: "trips_started", title: "Viagens iniciadas" },
  { key: "trips_finished", title: "Viagens finalizadas" },
  { key: "deliveries_completed", title: "Entregas por parte concluídas" },
  { key: "orders_with_completed_leg", title: "Pedidos com alguma parte entregue" },
  { key: "occurrences_registered", title: "Ocorrências registradas" },
  { key: "delivery_exceptions", title: "Exceções de entrega" },
  { key: "trips_canceled", title: "Cancelamentos de viagem" },
  { key: "interruption_events", title: "Interrupções e retomadas" },
];

export function ManagementReportsPanel() {
  const [from, setFrom] = useState(() => utcDate(-7));
  const [to, setTo] = useState(() => utcDate());
  const [truck, setTruck] = useState("");
  const [driver, setDriver] = useState("");
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [summary, setSummary] = useState<ManagementSummary | null>(null);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [effective, setEffective] = useState<ManagementFilters | null>(null);

  const refresh = useCallback(async (filters: ManagementFilters) => {
    setStatus("loading");
    setError("");
    try {
      const result = await fetchManagementSummary(filters);
      setSummary(result);
      setEffective(filters);
      setStatus("ready");
    } catch {
      setSummary(null);
      setEffective(null);
      setError("Falha ao consultar o resumo gerencial. Confira suas permissões, datas e filtros.");
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void refresh(makeFilters(utcDate(-7), utcDate(), "", ""));
  }, [refresh]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      void refresh(makeFilters(from, to, truck, driver));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Período inválido.");
    }
  }

  async function exportFile(format: "csv" | "pdf") {
    if (!effective || exporting) return;
    setExporting(true);
    setError("");
    try {
      await downloadManagementReport(format, effective);
    } catch {
      setError("Não foi possível exportar este resumo. Tente novamente.");
    } finally {
      setExporting(false);
    }
  }

  return <section className="report-block" aria-label="Relatório gerencial filtrado">
    <div className="report-block-head">
      <h2>Relatório gerencial filtrado</h2>
      <p>Fatos reais do PostgreSQL; período por data UTC, com fim exclusivo.</p>
    </div>
    <form onSubmit={submit} className="entity-toolbar">
      <label>De (UTC)<input type="date" value={from} onChange={(event) => setFrom(event.target.value)} required /></label>
      <label>Até (inclusive)<input type="date" value={to} onChange={(event) => setTo(event.target.value)} required /></label>
      <label>Caminhão (UUID opcional)<input value={truck} onChange={(event) => setTruck(event.target.value)} placeholder="Todos" maxLength={36} /></label>
      <label>Motorista (UUID opcional)<input value={driver} onChange={(event) => setDriver(event.target.value)} placeholder="Todos" maxLength={36} /></label>
      <button type="submit" className="btn-primary" disabled={status === "loading"}>Consultar</button>
    </form>
    <p className="entity-form-help">Um pedido com uma parte entregue não é necessariamente um pedido completamente entregue. Os indicadores respeitam essa distinção.</p>
    {error && <AlertBanner>{error}</AlertBanner>}
    {status === "loading" && <p role="status">Apurando dados do servidor…</p>}
    {status === "ready" && summary && <div className="management-kpis">
      {metrics.map(({ key, title }) => <div className="report-kpi" key={key}>
        <span className="report-kpi-label">{title}</span>
        <strong className="report-kpi-value">{summary[key] as number}</strong>
      </div>)}
    </div>}
    <div className="entity-form-actions">
      <button type="button" className="btn-secondary" disabled={!effective || exporting} onClick={() => void exportFile("csv")}>Exportar CSV</button>
      <button type="button" className="btn-secondary" disabled={!effective || exporting} onClick={() => void exportFile("pdf")}>Exportar PDF</button>
    </div>
  </section>;
}
