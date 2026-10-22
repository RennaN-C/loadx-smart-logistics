import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { listDeliveryCommunications, type DeliveryCommunication } from "../api/communicationsApi";
import { DeliveryCommunicationPanel } from "./DeliveryCommunicationPanel";
vi.mock("../api/communicationsApi");
const ITEM: DeliveryCommunication = { id: "n1", occurrence_id: "ocorrencia-1", event_type: "OCCURRENCE_REGISTERED", created_at: "2026-10-21T15:00:00Z", channel: "WHATSAPP_MOCK", simulation_status: "SIMULATED", processing_status: "SUCCEEDED" };
function page(items = [ITEM], n = 1, totalPages = 1) { return { items, page: n, pageSize: 20, total: items.length ? totalPages : 0, totalPages }; }
beforeEach(() => { vi.resetAllMocks(); vi.mocked(listDeliveryCommunications).mockResolvedValue(page()); });
describe("Comunicação real por entrega OC81", () => {
  it("mostra somente estados retornados e distingue simulação de envio real", async () => {
    render(<DeliveryCommunicationPanel deliveryId="d1" />);
    expect(await screen.findByText("Concluído no simulador")).toBeInTheDocument();
    expect(screen.getByText("WhatsApp simulado")).toBeInTheDocument();
    expect(screen.getByText(/não comprova envio, recebimento ou leitura/)).toBeInTheDocument();
    expect(listDeliveryCommunications).toHaveBeenCalledWith("d1", { page: 1, pageSize: 20 });
    expect(screen.queryByRole("button", { name: /Enviar/ })).not.toBeInTheDocument();
  });
  it("apresenta estado vazio sem fingir conversa ou pendência de processamento", async () => {
    vi.mocked(listDeliveryCommunications).mockResolvedValue(page([]));
    render(<DeliveryCommunicationPanel deliveryId="d1" />);
    await screen.findByText(/Nenhuma comunicação operacional/);
    expect(screen.queryByText("Concluído no simulador")).not.toBeInTheDocument();
  });
  it.each(["AUTH_INVALID_TOKEN", "AUTH_FORBIDDEN", "NETWORK_ERROR"])("permite retry seguro depois de %s", async code => {
    vi.mocked(listDeliveryCommunications).mockRejectedValueOnce(new ApiError(code, "texto interno sensível"));
    render(<DeliveryCommunicationPanel deliveryId="d1" />);
    await screen.findByRole("alert");
    expect(screen.queryByText("texto interno sensível")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await screen.findByText("Concluído no simulador");
  });
  it("pagina no servidor e recarrega a página selecionada", async () => {
    vi.mocked(listDeliveryCommunications).mockResolvedValue(page([ITEM], 1, 2));
    render(<DeliveryCommunicationPanel deliveryId="d1" />);
    await screen.findByRole("navigation", { name: "Paginação de comunicação" });
    vi.mocked(listDeliveryCommunications).mockResolvedValue(page([ITEM], 2, 2));
    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await screen.findByText("Página 2 de 2");
    fireEvent.click(screen.getByRole("button", { name: "Atualizar comunicação" }));
    await waitFor(() => expect(listDeliveryCommunications).toHaveBeenLastCalledWith("d1", { page: 2, pageSize: 20 }));
  });
  it("descarta respostas tardias ao trocar de entrega", async () => {
    let resolveOld!: (result: ReturnType<typeof page>) => void;
    vi.mocked(listDeliveryCommunications).mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
    const view = render(<DeliveryCommunicationPanel deliveryId="d1" />);
    view.rerender(<DeliveryCommunicationPanel deliveryId="d2" />);
    await screen.findByText("Concluído no simulador");
    resolveOld(page([{ ...ITEM, occurrence_id: "não-exibir-da-outra-entrega", simulation_status: "FAILED" }]));
    await waitFor(() => expect(screen.queryByText(/não-exibi/)).not.toBeInTheDocument());
    expect(screen.queryByText("Simulação falhou")).not.toBeInTheDocument();
  });
  it("mostra carregamento e não inventa fila em registros legados", async () => {
    let resolve!: (result: ReturnType<typeof page>) => void;
    vi.mocked(listDeliveryCommunications).mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    render(<DeliveryCommunicationPanel deliveryId="d1" />);
    expect(screen.getByRole("status")).toHaveTextContent("Consultando comunicação");
    resolve(page([{ ...ITEM, processing_status: null }]));
    await screen.findByText("Sem fila registrada");
  });
});
