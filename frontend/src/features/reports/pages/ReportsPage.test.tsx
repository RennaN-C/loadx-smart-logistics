import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import type { OrderListItem } from "../../orders/types";
import { ReportsPage } from "./ReportsPage";

let profileRole = "LOGISTICS_MANAGER";
vi.mock("../../auth/hooks/useAuth", () => ({ useAuth: () => ({ user: { role: profileRole } }) }));
vi.mock("../../orders/api/ordersApi");
vi.mock("../../customers/api/customersApi");

/** Bem no passado, para "atrasado" não depender de quando o teste roda. */
const VENCIDO = "2020-01-01T00:00:00Z";
/** Bem no futuro, pelo mesmo motivo. */
const NO_PRAZO = "2099-01-01T00:00:00Z";

function order(overrides: Partial<OrderListItem> = {}): OrderListItem {
  return {
    id: "o1",
    customerId: "c1",
    status: "READY",
    priority: "NORMAL",
    expectedDeliveryAt: null,
    createdAt: "2026-08-01T00:00:00Z",
    itemCount: 1,
    volumeCount: 1,
    ...overrides,
  };
}

const CUSTOMERS = [
  { id: "c1", name: "Distribuidora Aurora", active: true, city: "Campinas", state: "SP", createdAt: VENCIDO },
  { id: "c2", name: "Cliente viagem", active: true, city: "Sorocaba", state: "SP", createdAt: VENCIDO },
];

function arrange(orders: OrderListItem[], { customersFail = false } = {}) {
  vi.mocked(listOrders).mockResolvedValue(makePage(orders));
  if (customersFail) {
    vi.mocked(listCustomers).mockRejectedValue(new ApiError("FORBIDDEN", "sem acesso"));
  } else {
    vi.mocked(listCustomers).mockResolvedValue(makePage(CUSTOMERS));
  }
}

/**
 * Escopado na grade de indicadores: "PEDIDOS" e "VOLUMES" também são colunas do
 * relatório por cliente, e uma busca solta pegaria as duas.
 */
function kpi(rotulo: string) {
  const grade = document.querySelector(".report-kpis");
  if (grade === null) throw new Error("grade de indicadores ausente");

  const card = within(grade as HTMLElement).getByText(rotulo).closest(".report-kpi");
  return card?.querySelector(".report-kpi-value")?.textContent;
}

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    profileRole = "LOGISTICS_MANAGER";
  });

  it("apura os indicadores sobre os pedidos", async () => {
    arrange([
      order({ id: "a", status: "READY", itemCount: 1, volumeCount: 3 }),
      order({ id: "b", status: "IN_TRANSIT", itemCount: 1, volumeCount: 2 }),
      order({ id: "c", status: "DELIVERED", itemCount: 1, volumeCount: 90 }),
    ]);

    render(<ReportsPage />);

    await waitFor(() => expect(kpi("PEDIDOS")).toBe("3"));
    expect(kpi("EM ABERTO")).toBe("2");
    // o entregue não conta: já saiu do caminhão
    expect(kpi("VOLUMES EM ABERTO")).toBe("5");
    expect(kpi("ATRASADOS")).toBe("0");
  });

  it("conta como atrasado só o que venceu e não fechou", async () => {
    arrange([
      order({ id: "a", expectedDeliveryAt: VENCIDO }),
      order({ id: "b", expectedDeliveryAt: VENCIDO, status: "DELIVERED" }),
      order({ id: "c", expectedDeliveryAt: NO_PRAZO }),
    ]);

    render(<ReportsPage />);

    await waitFor(() => expect(kpi("ATRASADOS")).toBe("1"));
  });

  it("lista os atrasados com o nome do cliente resolvido", async () => {
    arrange([order({ customerId: "c2", expectedDeliveryAt: VENCIDO })]);

    render(<ReportsPage />);

    await waitFor(() => expect(screen.getByText("Pedidos atrasados")).toBeInTheDocument());
    const tabela = screen.getAllByRole("table")[0];
    expect(within(tabela).getByText("Cliente viagem")).toBeInTheDocument();
  });

  it("esconde o bloco de atrasados quando não há nenhum", async () => {
    arrange([order({ expectedDeliveryAt: NO_PRAZO })]);

    render(<ReportsPage />);

    await waitFor(() => expect(screen.getByText("Por situação")).toBeInTheDocument());
    expect(screen.queryByText("Pedidos atrasados")).not.toBeInTheDocument();
  });

  it("segue funcionando quando o perfil não lê clientes", async () => {
    // conferente: 403 em /customers não pode derrubar o relatório
    arrange([order()], { customersFail: true });

    render(<ReportsPage />);

    await waitFor(() => expect(kpi("PEDIDOS")).toBe("1"));
    expect(screen.getByText(/Dados por cliente não estão disponíveis/)).toBeInTheDocument();
    expect(screen.queryByText("Por cliente")).not.toBeInTheDocument();
  });

  it("avisa quando não há pedido para apurar, em vez de mostrar zeros", async () => {
    arrange([]);

    render(<ReportsPage />);

    await waitFor(() =>
      expect(screen.getByText(/Ainda não há pedidos para apurar/)).toBeInTheDocument(),
    );
    expect(document.querySelector(".report-kpis")).toBeNull();
  });

  it("mostra erro quando a listagem de pedidos falha", async () => {
    vi.mocked(listOrders).mockRejectedValue(new ApiError("UNKNOWN_ERROR", "falhou"));
    vi.mocked(listCustomers).mockResolvedValue(makePage(CUSTOMERS));

    render(<ReportsPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/Não foi possível apurar/);
  });
  it("usa volumes físicos tanto no total quanto nas tabelas", async () => {
    arrange([order({ itemCount: 2, volumeCount: 19, expectedDeliveryAt: VENCIDO })]);
    render(<ReportsPage />);
    await waitFor(() => expect(kpi("VOLUMES EM ABERTO")).toBe("19"));
    for (const table of screen.getAllByRole("table")) expect(within(table).getByText("19")).toBeInTheDocument();
    expect(screen.getByText(/até 1.000 pedidos/)).toBeInTheDocument();
  });

  it("conferente não faz a consulta de clientes protegida", async () => {
    profileRole = "CHECKER";
    arrange([order()]);
    render(<ReportsPage />);
    await waitFor(() => expect(kpi("PEDIDOS")).toBe("1"));
    expect(listCustomers).not.toHaveBeenCalled();
    expect(screen.queryByText("Por cliente")).not.toBeInTheDocument();
  });

  it("sinaliza quantidades físicas ausentes sem números inventados", async () => {
    arrange([order({ itemCount: 2, volumeCount: undefined, expectedDeliveryAt: VENCIDO })]);
    render(<ReportsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Volumes físicos não informados/);
    expect(kpi("VOLUMES EM ABERTO")).toBe("—");
  });

  it("limita a mil pedidos e informa a parcela não apurada", async () => {
    vi.mocked(listCustomers).mockResolvedValue(makePage(CUSTOMERS));
    vi.mocked(listOrders).mockImplementation(async (params) => ({ ...makePage(Array.from({ length: 100 }, (_, index) => order({ id: `${params?.page}-${index}` }))), page: params?.page ?? 1, total: 1001, totalPages: 11 }));
    render(<ReportsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("1 pedido(s) ficaram fora");
    expect(kpi("PEDIDOS")).toBe("1000");
    expect(listOrders).toHaveBeenCalledTimes(10);
  });

  it("repete a consulta após erro sem afetar os contratos PDF", async () => {
    vi.mocked(listOrders).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "sem rede")).mockResolvedValue(makePage([order()]));
    vi.mocked(listCustomers).mockResolvedValue(makePage(CUSTOMERS));
    render(<ReportsPage />);
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Recarregar" }));
    await waitFor(() => expect(kpi("PEDIDOS")).toBe("1"));
  });

});
