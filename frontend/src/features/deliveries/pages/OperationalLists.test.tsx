import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { listDeliveries, listLoadingSessions } from "../api/operationalListsApi";
import { DeliveryListPage } from "./DeliveryListPage";
import { LoadingListPage } from "./LoadingListPage";

vi.mock("../api/operationalListsApi");
const loading = { id: "12345678-loading", loadPlanId: "87654321-plan", status: "IN_PROGRESS" as const, startedAt: "2026-10-23T10:00:00Z", finishedAt: null };
const delivery = { id: "12345678-delivery", tripId: "trip-origin", orderId: "87654321-order", status: "DELIVERED" as const, sequence: 2, deliveredAt: "2026-10-23T11:00:00Z" };
function page<T>(items: T[], current = 1, totalPages = 1) {
  return { items, page: current, pageSize: 20, total: items.length ? totalPages * 20 : 0, totalPages };
}
function open(element: ReactNode) { return render(<MemoryRouter>{element}</MemoryRouter>); }
beforeEach(() => {
  vi.mocked(listLoadingSessions).mockReset().mockResolvedValue(page([loading]));
  vi.mocked(listDeliveries).mockReset().mockResolvedValue(page([delivery]));
});

describe("central operacional", () => {
  it.each([["PENDING", "Não iniciado"], ["IN_PROGRESS", "Em conferência"], ["FINISHED", "Concluído"]] as const)("traduz carregamento %s e identifica o recurso", async (status, label) => {
    vi.mocked(listLoadingSessions).mockResolvedValue(page([{ ...loading, status }]));
    open(<LoadingListPage />);
    const table = await screen.findByRole("table");
    expect(within(table).getByText(label)).toBeVisible();
    expect(within(table).getByRole("rowheader")).toHaveTextContent("#12345678Plano #87654321");
    expect(within(table).queryByText(status)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir carregamento #12345678" })).toHaveAttribute("href", `/loading/${loading.id}`);
  });
  it.each([["PENDING", "Pendente"], ["IN_DELIVERY", "Em entrega"], ["DELIVERED", "Entregue"], ["CANCELED", "Cancelada"]] as const)("distingue entrega %s sem confundir aprovação com conclusão", async (status, label) => {
    vi.mocked(listDeliveries).mockResolvedValue(page([{ ...delivery, status }]));
    open(<DeliveryListPage />);
    const table = await screen.findByRole("table");
    expect(within(table).getByText(label)).toBeVisible();
    expect(within(table).getByRole("rowheader")).toHaveTextContent("Pedido #87654321");
    expect(screen.getByRole("link", { name: "Abrir viagem da entrega #12345678" })).toHaveAttribute("href", "/trips/trip-origin");
    expect(within(table).queryByText(status)).not.toBeInTheDocument();
  });
  it("pagina carregamentos no servidor e reinicia ao filtrar", async () => {
    vi.mocked(listLoadingSessions).mockImplementation(async (params) => page([loading], params?.page, 2));
    open(<LoadingListPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(listLoadingSessions).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
    fireEvent.change(screen.getByRole("combobox", { name: "Situação do carregamento" }), { target: { value: "FINISHED" } });
    await waitFor(() => expect(listLoadingSessions).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, status: "FINISHED" })));
  });
  it("pagina e filtra entregas no servidor, incluindo canceladas", async () => {
    vi.mocked(listDeliveries).mockImplementation(async (params) => page([delivery], params?.page, 2));
    open(<DeliveryListPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(listDeliveries).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
    fireEvent.change(screen.getByRole("combobox", { name: "Situação da entrega" }), { target: { value: "CANCELED" } });
    await waitFor(() => expect(listDeliveries).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, status: "CANCELED" })));
  });
  it("traduz erro de rede e recupera carregamentos na nova tentativa", async () => {
    vi.mocked(listLoadingSessions).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "technical network failure"));
    open(<LoadingListPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Verifique sua conexão");
    expect(screen.queryByText("technical network failure")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("table")).toBeVisible();
  });
  it("explica negativa de acesso às entregas sem oferecer criação", async () => {
    vi.mocked(listDeliveries).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Forbidden"));
    open(<DeliveryListPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("não tem permissão");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("orienta filtro sem resultado e restaura a consulta completa", async () => {
    vi.mocked(listDeliveries).mockImplementation(async (params) => page(params?.status ? [] : [delivery]));
    open(<DeliveryListPage />);
    await screen.findByRole("table");
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "PENDING" } });
    expect(await screen.findByText(/Nenhuma entrega nesta situação/)).toBeVisible();
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "" } });
    expect(await screen.findByRole("table")).toBeVisible();
    expect(listDeliveries).toHaveBeenLastCalledWith(expect.objectContaining({ status: undefined }));
  });
  it("anuncia carregamento sem apresentar lista vazia como resultado", () => {
    vi.mocked(listLoadingSessions).mockReturnValue(new Promise(() => {}));
    open(<LoadingListPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando carregamentos");
    expect(screen.queryByText(/Nenhum carregamento encontrado/)).not.toBeInTheDocument();
  });
});
