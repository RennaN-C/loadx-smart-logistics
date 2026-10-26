import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Modal } from "../../../components/Modal";
import { Pagination } from "../../../components/Pagination";
import { AlertBanner } from "../../../components/AlertBanner";
import type { Page } from "../../../types/api";
import { ApiError } from "../../../types/api";
import { getOutboxAttempts, getOutboxEvent, getOutboxSource, getOutboxSummary, listOutbox, retryOutbox, type OutboxAttempt, type OutboxEvent, type OutboxState, type OutboxSummary, type OutboxType } from "../api/outboxApi";
import "./OutboxPanel.css";

const OUTBOX_LABELS: Record<OutboxState, string> = { PENDING: "Pendente", PROCESSING: "Processando", SUCCEEDED: "Concluído", RETRYABLE: "Aguardando retentativa", TERMINAL: "Falha terminal", UNCERTAIN: "Resultado incerto" };
const TYPES: Record<OutboxType, string> = { TRIP_STARTED: "Viagem iniciada", OCCURRENCE_REGISTERED: "Ocorrência registrada" };
const ERRORS: Record<string, string> = { TRANSIENT: "Falha temporária antes do efeito", PERMANENT: "Rejeição definitiva do transporte", TIMEOUT_UNKNOWN: "Tempo esgotado; resultado desconhecido", UNKNOWN_RESULT: "Resultado não confirmado", LEASE_EXPIRED: "Worker interrompido ou prazo expirado", EXHAUSTED: "Limite de tentativas atingido", LEGACY_FAILED: "Falha registrada pela versão anterior", LEGACY_UNKNOWN: "Tentativa anterior sem resultado confirmado", NO_RECIPIENT: "Destinatário atual indisponível" };
const eligible = (state: OutboxState) => ["RETRYABLE", "TERMINAL", "UNCERTAIN"].includes(state);
const date = (value: string) => new Date(value).toLocaleString("pt-BR");
const errorText = (code: string | null) => code ? ERRORS[code] ?? "Falha sanitizada do transporte" : "Sem falha registrada";
const badge = (status: OutboxState) => <span className="outbox-badge" data-status={status}>{OUTBOX_LABELS[status]}</span>;

export function OutboxPanel() {
  const [params] = useSearchParams();
  const location = useLocation();
  function setParams(update: (current: URLSearchParams) => URLSearchParams) {
    const next = update(new URLSearchParams(params));
    navigate({ pathname: location.pathname, search: next.toString(), hash: location.hash });
  }
  const navigate = useNavigate();
  const rawPage = Number(params.get("queue_page"));
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const rawStatus = params.get("queue_status");
  const status = rawStatus && Object.keys(OUTBOX_LABELS).includes(rawStatus) ? rawStatus as OutboxState : undefined;
  const rawType = params.get("queue_type");
  const eventType = rawType && Object.keys(TYPES).includes(rawType) ? rawType as OutboxType : undefined;
  const order = params.get("queue_order") === "asc" ? "asc" : "desc";
  const selected = params.get("queue_event");
  const [result, setResult] = useState<Page<OutboxEvent> | null>(null);
  const [summary, setSummary] = useState<OutboxSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [event, setEvent] = useState<OutboxEvent | null>(null);
  const [attempts, setAttempts] = useState<Page<OutboxAttempt> | null>(null);
  const [attemptPage, setAttemptPage] = useState(1);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const commands = useRef(new Map<string, string>());
  const noticeRef = useRef<HTMLOutputElement>(null);
  const actionGeneration = useRef(0);
  useEffect(() => { if (notice) noticeRef.current?.focus(); }, [notice]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setResult(null); setSummary(null);
    void Promise.allSettled([
      listOutbox({ page, page_size: 20, status, event_type: eventType, sort_order: order }, controller.signal),
      getOutboxSummary(controller.signal),
    ]).then(([rows, totals]) => {
      if (controller.signal.aborted) return;
      const denied = [rows, totals].some((item) => item.status === "rejected" && item.reason instanceof ApiError && [401, 403].includes(item.reason.status ?? 0));
      if (denied) { setError("A consulta da fila exige uma sessão ADMIN válida."); return; }
      if (rows.status === "fulfilled") setResult(rows.value);
      if (totals.status === "fulfilled") setSummary(totals.value);
      if (rows.status === "rejected" || totals.status === "rejected") setError("Parte da consulta não está disponível. Atualize para tentar novamente.");
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, status, eventType, order, refresh]);
  useEffect(() => {
    actionGeneration.current += 1;
    setConfirm(false); setDetailError(""); setEvent(null); setAttempts(null);
    if (!selected) return;
    const controller = new AbortController();
    setDetailLoading(true);
    void Promise.all([getOutboxEvent(selected, controller.signal), getOutboxAttempts(selected, attemptPage, controller.signal)])
      .then(([item, history]) => { if (!controller.signal.aborted) { setEvent(item); setAttempts(history); } })
      .catch(() => { if (!controller.signal.aborted) setDetailError("Não foi possível consultar o evento e seu histórico."); })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [selected, attemptPage, refresh]);
  useEffect(() => () => { actionGeneration.current += 1; }, []);
  function filter(key: string, value: string) {
    setNotice(""); setParams((current) => { const next = new URLSearchParams(current); next.delete("queue_page"); if (value) { next.set(key, value); } else { next.delete(key); } return next; });
  }
  function choose(id: string | null) {
    setAttemptPage(1); setParams((current) => { const next = new URLSearchParams(current); if (id) { next.set("queue_event", id); } else { next.delete("queue_event"); } return next; });
  }
  async function reprocess() {
    if (!event || busy) return;
    const generation = actionGeneration.current;
    const key = `${event.id}:${event.updated_at}`;
    let command = commands.current.get(key);
    if (!command) { command = crypto.randomUUID(); commands.current.set(key, command); }
    setBusy(true); setDetailError("");
    try {
      await retryOutbox(event.id, command);
      if (generation !== actionGeneration.current) return;
      setConfirm(false); choose(null); setNotice("Reprocessamento registrado. Acompanhe a nova tentativa na fila."); setRefresh((value) => value + 1);
    } catch { if (generation === actionGeneration.current) setDetailError("Não foi possível confirmar o comando. Ao repetir, a mesma identificação será utilizada com segurança."); }
    finally { setBusy(false); }
  }
  async function openSource() {
    if (!event || busy) return;
    const generation = actionGeneration.current;
    setBusy(true); setDetailError("");
    try { const href = await getOutboxSource(event.id); if (generation === actionGeneration.current) navigate(href); }
    catch { if (generation === actionGeneration.current) setDetailError("A origem está indisponível ou seu acesso foi alterado."); }
    finally { setBusy(false); }
  }
  return <div className="outbox-panel" aria-busy={loading}>
    <div className="outbox-toolbar"><div><p className="outbox-kicker">Confiabilidade operacional</p><h3>Fila de eventos e reprocessamento</h3><p>Histórico persistente dos canais de saída. WhatsApp exclusivamente simulado.</p></div><button className="btn-secondary" type="button" disabled={loading || busy} onClick={() => setRefresh((value) => value + 1)}>Atualizar fila</button></div>
    {summary && <dl className="outbox-metrics" aria-label="Resumo da fila">
      <div><dt>Pendentes</dt><dd>{summary.counts.PENDING + summary.counts.RETRYABLE}</dd></div><div><dt>Processando</dt><dd>{summary.counts.PROCESSING}</dd></div><div><dt>Concluídos</dt><dd>{summary.counts.SUCCEEDED}</dd></div><div><dt>Com falha ou incertos</dt><dd>{summary.counts.TERMINAL + summary.counts.UNCERTAIN}</dd></div>
    </dl>}
    {summary?.oldest_pending_at && <p className="outbox-note">Pendente mais antigo: <time dateTime={summary.oldest_pending_at}>{date(summary.oldest_pending_at)}</time></p>}
    <div className="outbox-filters">
      <label>Situação do evento<select value={status ?? ""} disabled={busy} onChange={(e) => filter("queue_status", e.target.value)}><option value="">Todas</option>{Object.entries(OUTBOX_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Tipo de evento<select value={eventType ?? ""} disabled={busy} onChange={(e) => filter("queue_type", e.target.value)}><option value="">Todos</option>{Object.entries(TYPES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Ordenação da fila<select value={order} disabled={busy} onChange={(e) => filter("queue_order", e.target.value)}><option value="desc">Mais recentes primeiro</option><option value="asc">Mais antigos primeiro</option></select></label>
    </div>
    {notice && <output ref={noticeRef} tabIndex={-1} className="outbox-success">{notice}</output>}
    {error && <div className="outbox-feedback"><AlertBanner>{error}</AlertBanner><button type="button" className="btn-secondary" disabled={loading} onClick={() => setRefresh((value) => value + 1)}>Tentar novamente</button></div>}
    {loading && <output className="outbox-feedback">Consultando eventos persistidos…</output>}
    {!loading && result && (result.items.length ? <div className="outbox-table-wrap"><table className="outbox-table"><caption className="sr-only">Eventos de saída persistidos</caption><thead><tr><th scope="col">Evento</th><th scope="col">Situação</th><th scope="col">Tentativas no ciclo</th><th scope="col">Criado em</th><th scope="col">Ação</th></tr></thead><tbody>{result.items.map((item) => <tr key={item.id}>
      <td data-label="Evento"><strong>{TYPES[item.event_type]}</strong><span className="outbox-id">{item.id}</span><small>WhatsApp · Simulado</small></td><td data-label="Situação">{badge(item.status)}</td><td data-label="Tentativas no ciclo">{item.attempt_count}</td><td data-label="Criado em"><time dateTime={item.created_at}>{date(item.created_at)}</time></td><td data-label="Ação"><button type="button" className="btn-secondary" onClick={() => choose(item.id)} aria-label={`Detalhes do evento ${item.id}`}>Detalhes</button></td>
    </tr>)}</tbody></table></div> : <div className="outbox-empty"><h3>Nenhum evento encontrado</h3><p>Os eventos persistidos aparecerão aqui. Ajuste os filtros para consultar outras situações.</p></div>)}
    {!loading && result && <Pagination label="eventos" page={result.page} totalPages={result.totalPages} onChange={(value) => setParams((current) => { const next = new URLSearchParams(current); next.set("queue_page", String(value)); return next; })} />}
    <p className="outbox-note">A caixa pessoal é independente do canal. Resultado incerto exige revisão; não há repetição automática de envios sem confirmação.</p>
    {selected && <div aria-hidden={confirm || undefined}><Modal title="Detalhes do evento" subtitle="Canal WhatsApp simulado · contrato v1" onClose={() => { if (!busy) choose(null); }}>
      {detailLoading && <output>Carregando evento e tentativas…</output>}
      {detailError && <AlertBanner>{detailError}</AlertBanner>}
      {!detailLoading && event && <div className="outbox-detail">{badge(event.status)}<dl><div><dt>Evento</dt><dd className="outbox-id">{event.id}</dd></div><div><dt>Notificação de origem</dt><dd className="outbox-id">{event.notification_id}</dd></div><div><dt>Correlação</dt><dd className="outbox-id">{event.correlation_id}</dd></div><div><dt>Último resultado</dt><dd>{errorText(event.last_error_code)}</dd></div>{["PENDING", "RETRYABLE"].includes(event.status) && <div><dt>Disponível para tentativa a partir de</dt><dd>{date(event.next_attempt_at)}</dd></div>}{event.lease_expires_at && <div><dt>Prazo do processamento</dt><dd>{date(event.lease_expires_at)}</dd></div>}</dl>
      <h3>Histórico de tentativas</h3>{attempts?.items.length ? <ol className="outbox-attempts">{attempts.items.map((item) => <li key={item.id}><div><strong>{item.origin === "LEGACY" ? "Tentativa legada" : `Tentativa ${item.generation}`}</strong>{badge(item.result)}</div><time dateTime={item.started_at}>{date(item.started_at)}</time><p>{errorText(item.error_code)}</p>{item.finished_at && <small>Encerrada em {date(item.finished_at)}</small>}</li>)}</ol> : <p>Nenhuma tentativa registrada.</p>}
      {attempts && <Pagination label="tentativas" page={attempts.page} totalPages={attempts.totalPages} onChange={setAttemptPage} />}
      <div className="outbox-actions"><button type="button" className="btn-secondary" disabled={busy} onClick={() => void openSource()}>Abrir operação de origem</button>{eligible(event.status) && <button type="button" className="btn-primary" disabled={busy} onClick={() => setConfirm(true)}>Reprocessar evento</button>}</div></div>}
      <div className="outbox-actions"><button type="button" className="btn-secondary" disabled={busy} onClick={() => choose(null)}>Fechar detalhes</button>{detailError && <button type="button" className="btn-secondary" disabled={busy} onClick={() => setRefresh((value) => value + 1)}>Consultar novamente</button>}</div>
    </Modal></div>}
    {confirm && event && <Modal title="Confirmar reprocessamento" onClose={() => { if (!busy) setConfirm(false); }}><p>Uma nova tentativa será agendada para este evento simulado. O histórico será preservado e a ação será auditada.</p>{event.status === "UNCERTAIN" && <AlertBanner>A tentativa anterior não teve resultado confirmado. A repetição explícita é permitida apenas porque este canal é simulado.</AlertBanner>}{detailError && <AlertBanner>{detailError}</AlertBanner>}<div className="outbox-actions"><button className="btn-secondary" type="button" disabled={busy} onClick={() => setConfirm(false)}>Cancelar</button><button className="btn-primary" type="button" disabled={busy} onClick={() => void reprocess()}>{busy ? "Registrando…" : "Confirmar reprocessamento"}</button></div></Modal>}
  </div>;
}
