import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import * as api from "../api/outboxApi";
import { OutboxPanel } from "./OutboxPanel";
vi.mock("../api/outboxApi");
const ITEM: api.OutboxEvent = { id: "00000000-0000-4000-8000-000000000109", notification_id: "fato", channel: "WHATSAPP_MOCK", event_type: "TRIP_STARTED", contract_version: 1, correlation_id: "correlação", status: "UNCERTAIN", attempt_count: 1, generation: 1, next_attempt_at: "2026-10-20T12:00:00Z", lease_expires_at: null, last_error_code: "TIMEOUT_UNKNOWN", created_at: "2026-10-20T12:00:00Z", updated_at: "2026-10-20T12:01:00Z" };
const PAGE = { items: [ITEM], page: 1, pageSize: 20, total: 1, totalPages: 1 };
function Location() { const location = useLocation(); return <output aria-label="URL atual">{location.pathname}{location.search}{location.hash}</output>; }
function renderPanel(url = "/settings#settings-outbox") { return render(<MemoryRouter initialEntries={[url]}><OutboxPanel /><Location /></MemoryRouter>); }
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.listOutbox).mockResolvedValue(PAGE);
  vi.mocked(api.getOutboxSummary).mockResolvedValue({ counts: { PENDING: 2, PROCESSING: 1, SUCCEEDED: 3, RETRYABLE: 1, TERMINAL: 1, UNCERTAIN: 1 }, oldest_pending_at: ITEM.created_at });
  vi.mocked(api.getOutboxEvent).mockResolvedValue(ITEM);
  vi.mocked(api.getOutboxAttempts).mockResolvedValue({ items: [{ id: "attempt", generation: 1, origin: "WORKER", started_at: ITEM.created_at, finished_at: ITEM.updated_at, result: "UNCERTAIN", error_code: "TIMEOUT_UNKNOWN" }], page: 1, pageSize: 10, total: 1, totalPages: 1 });
  vi.mocked(api.retryOutbox).mockResolvedValue({ ...ITEM, status: "PENDING" });
  vi.mocked(api.getOutboxSource).mockResolvedValue("/trips/origem");
});
describe("OC109: fila administrativa", () => {
  it("consulta estados reais e apresenta canal simulado e resultado incerto", async () => {
    renderPanel();
    expect(screen.getByText("Consultando eventos persistidos…")).toBeInTheDocument();
    await screen.findByRole("button", { name: `Detalhes do evento ${ITEM.id}` });
    expect(screen.getByRole("cell", { name: "Resultado incerto" })).toBeInTheDocument();
    expect(screen.getByText("WhatsApp · Simulado")).toBeInTheDocument();
    expect(screen.getByText("Pendentes")).toBeInTheDocument();
  });
  it("filtros preservam seção e usam contrato da API", async () => {
    renderPanel();
    await screen.findByRole("cell", { name: "Resultado incerto" });
    fireEvent.change(screen.getByLabelText("Situação do evento"), { target: { value: "TERMINAL" } });
    await waitFor(() => expect(api.listOutbox).toHaveBeenLastCalledWith(expect.objectContaining({ status: "TERMINAL", page: 1 }), expect.any(AbortSignal)));
    expect(screen.getByLabelText("URL atual")).toHaveTextContent("#settings-outbox");
    fireEvent.change(screen.getByLabelText("Tipo de evento"), { target: { value: "OCCURRENCE_REGISTERED" } });
    fireEvent.change(screen.getByLabelText("Ordenação da fila"), { target: { value: "asc" } });
    await waitFor(() => expect(api.listOutbox).toHaveBeenLastCalledWith(expect.objectContaining({ event_type: "OCCURRENCE_REGISTERED", sort_order: "asc" }), expect.any(AbortSignal)));
  });
  it("abre detalhe por URL e restaura histórico paginado", async () => {
    vi.mocked(api.getOutboxAttempts).mockResolvedValue({ items: [], page: 1, pageSize: 10, total: 11, totalPages: 2 });
    renderPanel(`/settings?queue_event=${ITEM.id}#settings-outbox`);
    const dialog = await screen.findByRole("dialog", { name: "Detalhes do evento" });
    await within(dialog).findByText("Nenhuma tentativa registrada.");
    fireEvent.click(within(dialog).getByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(api.getOutboxAttempts).toHaveBeenLastCalledWith(ITEM.id, 2, expect.any(AbortSignal)));
  });
  it("confirma reprocessamento incerto e mantém comando em falha de rede", async () => {
    vi.mocked(api.retryOutbox).mockRejectedValueOnce(new Error("segredo token")).mockResolvedValueOnce({ ...ITEM, status: "PENDING" });
    renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: `Detalhes do evento ${ITEM.id}` }));
    fireEvent.click(await screen.findByRole("button", { name: "Reprocessar evento" }));
    const confirm = screen.getByRole("dialog", { name: "Confirmar reprocessamento" });
    expect(within(confirm).getByRole("alert")).toHaveTextContent("canal é simulado");
    expect(api.retryOutbox).not.toHaveBeenCalled();
    fireEvent.click(within(confirm).getByRole("button", { name: "Confirmar reprocessamento" }));
    await waitFor(() => expect(within(confirm).getAllByRole("alert")).toHaveLength(2));
    expect(screen.queryByText(/segredo token/)).not.toBeInTheDocument();
    fireEvent.click(within(confirm).getByRole("button", { name: "Confirmar reprocessamento" }));
    await screen.findByText(/Reprocessamento registrado/);
    expect(api.retryOutbox).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.retryOutbox).mock.calls[0]).toEqual(vi.mocked(api.retryOutbox).mock.calls[1]);
  });
  it("cancelar confirmação não envia comando", async () => {
    renderPanel(`/settings?queue_event=${ITEM.id}#settings-outbox`);
    fireEvent.click(await screen.findByRole("button", { name: "Reprocessar evento" }));
    fireEvent.click(within(screen.getByRole("dialog", { name: "Confirmar reprocessamento" })).getByRole("button", { name: "Cancelar" }));
    expect(api.retryOutbox).not.toHaveBeenCalled();
  });
  it.each(["PENDING", "PROCESSING", "SUCCEEDED"] as const)("não oferece reprocessamento para %s", async (status) => {
    vi.mocked(api.getOutboxEvent).mockResolvedValue({ ...ITEM, status });
    renderPanel(`/settings?queue_event=${ITEM.id}#settings-outbox`);
    await screen.findByText("Tentativa 1");
    expect(screen.queryByRole("button", { name: "Reprocessar evento" })).not.toBeInTheDocument();
  });
  it("revalida acesso antes de navegar para origem", async () => {
    renderPanel(`/settings?queue_event=${ITEM.id}#settings-outbox`);
    fireEvent.click(await screen.findByRole("button", { name: "Abrir operação de origem" }));
    await waitFor(() => expect(screen.getByLabelText("URL atual")).toHaveTextContent("/trips/origem"));
    expect(api.getOutboxSource).toHaveBeenCalledWith(ITEM.id);
  });
  it("falha parcial preserva dados reais com retry", async () => {
    vi.mocked(api.getOutboxSummary).mockRejectedValueOnce(new Error("credencial"));
    renderPanel();
    expect(await screen.findByRole("alert")).toHaveTextContent("Parte da consulta");
    expect(screen.getByRole("cell", { name: "Resultado incerto" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await screen.findByText("Pendentes");
    await waitFor(() => expect(api.getOutboxSummary).toHaveBeenCalledTimes(2));
  });
  it.each([401,403])("remove resultados quando autorização falha (%s)", async (status) => {
    vi.mocked(api.getOutboxSummary).mockRejectedValue(new ApiError("FORBIDDEN", "segredo", [], status));
    renderPanel();
    expect(await screen.findByRole("alert")).toHaveTextContent("ADMIN válida");
    expect(screen.queryByRole("cell", { name: "Resultado incerto" })).not.toBeInTheDocument();
  });
  it("lista vazia não cria eventos fictícios", async () => {
    vi.mocked(api.listOutbox).mockResolvedValue({ ...PAGE, items: [], total: 0, totalPages: 0 });
    renderPanel(); await screen.findByText("Nenhum evento encontrado");
    expect(api.retryOutbox).not.toHaveBeenCalled();
  });
  it("Escape fecha o detalhe e devolve foco", async () => {
    renderPanel();
    const button = await screen.findByRole("button", { name: `Detalhes do evento ${ITEM.id}` });
    button.focus(); fireEvent.click(button);
    await screen.findByRole("button", { name: "Reprocessar evento" });
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(button).toHaveFocus();
  });
});
