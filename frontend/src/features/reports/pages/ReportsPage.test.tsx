import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { listCustomers } from "../../customers/api/customersApi";
import { listOrders } from "../../orders/api/ordersApi";
import type { OrderListItem } from "../../orders/types";
import { ReportsPage } from "./ReportsPage";

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
    ...overrides,
  };
}

const CUSTOMERS = [
  { id: "c1", name: "Distribuidora Aurora", city: "Campinas", state: "SP", createdAt: VENCIDO },
  { id: "c2", name: "Cliente viagem", city: "Sorocaba", state: "SP", createdAt: VENCIDO },
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
  });

  it("apura os indicadores sobre os pedidos", async () => {
    arrange([
      order({ id: "a", status: "READY", itemCount: 3 }),
      order({ id: "b", status: "IN_TRANSIT", itemCount: 2 }),
      order({ id: "c", status: "DELIVERED", itemCount: 90 }),
    ]);

    render(<ReportsPage />);

    await waitFor(() => expect(kpi("PEDIDOS")).toBe("3"));
    expect(kpi("EM ABERTO")).toBe("2");
    // o entregue não conta: já saiu do caminhão
    expect(kpi("VOLUMES A CARREGAR")).toBe("5");
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
    expect(screen.getByText(/conferente não lê dados de clientes/)).toBeInTheDocument();
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
});
