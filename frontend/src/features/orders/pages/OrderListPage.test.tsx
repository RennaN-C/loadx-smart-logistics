import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listProducts } from "../../products/api/productsApi";
import { getOrder, listOrders } from "../api/ordersApi";
import type { OrderListItem } from "../types";
import { OrderListPage } from "./OrderListPage";

vi.mock("../api/ordersApi");
vi.mock("../../customers/api/customersApi");
vi.mock("../../products/api/productsApi");
vi.mock("../../auth/hooks/useAuth");

const ORDERS: OrderListItem[] = [
  {
    id: "o1",
    customerId: "c1",
    status: "DRAFT",
    priority: "NORMAL",
    expectedDeliveryAt: null,
    createdAt: "2026-08-01T00:00:00Z",
    itemCount: 2,
  },
  {
    id: "o2",
    customerId: "c2",
    status: "DELIVERED",
    priority: "URGENT",
    expectedDeliveryAt: null,
    createdAt: "2026-08-02T00:00:00Z",
    itemCount: 1,
  },
];

const ORDER_FULL = {
  ...ORDERS[0],
  deliveryAddress: "Av. Brasil, 500",
  items: [{ id: "i1", orderId: "o1", productId: "p1", quantity: 4, deliverySequence: 1 }],
};

function mockRole(role: "LOGISTICS_MANAGER" | "CHECKER") {
  vi.mocked(useAuth).mockReturnValue({
    status: "authenticated",
    user: {
      id: "u1",
      name: "Ana Souza",
      email: "ana@example.test",
      role,
      active: true,
      createdAt: "2026-08-01T00:00:00Z",
    },
    login: vi.fn(),
    logout: vi.fn(),
  });
}

describe("OrderListPage", () => {
  beforeEach(() => {
    vi.mocked(listOrders).mockReset().mockResolvedValue(makePage(ORDERS));
    vi.mocked(getOrder).mockReset().mockResolvedValue(ORDER_FULL);
    vi.mocked(listCustomers)
      .mockReset()
      .mockResolvedValue(makePage([
        {
          id: "c1",
          name: "Distribuidora Aurora",
          document: "1",
          phone: null,
          address: "Rua A",
          city: "Campinas",
          state: "SP",
          notes: null,
          createdAt: "2026-08-01T00:00:00Z",
        },
      ]));
    vi.mocked(listProducts)
      .mockReset()
      .mockResolvedValue(makePage([
        {
          id: "p1",
          code: "CX-100",
          name: "Caixa média",
          description: null,
          widthCm: 40,
          heightCm: 30,
          lengthCm: 60,
          weightKg: 12.5,
          fragile: false,
          stackable: true,
          rotationAllowed: true,
          createdAt: "2026-08-01T00:00:00Z",
        },
      ]));
    mockRole("LOGISTICS_MANAGER");
  });

  it("resolve o nome do cliente a partir do id, que é tudo que a listagem traz", async () => {
    render(<OrderListPage />);

    expect(await screen.findByText("Distribuidora Aurora")).toBeInTheDocument();
  });

  it("avisa quando o cliente não está na página carregada, em vez de deixar vazio", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    // c2 não veio na listagem paginada de clientes
    expect(screen.getByText("Cliente não encontrado")).toBeInTheDocument();
  });

  it("mostra a contagem de itens, já que a listagem não devolve os itens", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    const grid = within(document.querySelector(".entity-grid") as HTMLElement);

    expect(grid.getByText("2")).toBeInTheDocument();
  });

  it("busca o pedido completo antes de abrir a edição", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.click(screen.getAllByRole("button", { name: "Editar" })[0]);

    await waitFor(() => expect(getOrder).toHaveBeenCalledWith("o1"));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    // endereço e itens só existem no detalhe
    expect(screen.getByLabelText("ENDEREÇO DE ENTREGA")).toHaveValue("Av. Brasil, 500");
  });

  it("traduz situação e prioridade para português nos cards", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    // escopado à grade: os mesmos rótulos aparecem nas opções do filtro
    const grid = within(document.querySelector(".entity-grid") as HTMLElement);

    expect(grid.getByText("Rascunho")).toBeInTheDocument();
    expect(grid.getByText("Entregue")).toBeInTheDocument();
    expect(grid.getByText("Urgente")).toBeInTheDocument();
  });

  it("filtra por situação", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.change(screen.getByLabelText("Filtrar por situação"), { target: { value: "DELIVERED" } });

    expect(screen.queryByText("Distribuidora Aurora")).not.toBeInTheDocument();
    expect(screen.getByText("Cliente não encontrado")).toBeInTheDocument();
  });

  it("busca por cliente sem chamar o backend de novo", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.change(screen.getByLabelText("Buscar por cliente"), { target: { value: "aurora" } });

    expect(screen.getByText("Distribuidora Aurora")).toBeInTheDocument();
    expect(screen.queryByText("Cliente não encontrado")).not.toBeInTheDocument();
    expect(listOrders).toHaveBeenCalledOnce();
  });

  it("esconde as ações de gestão para quem só tem leitura", async () => {
    mockRole("CHECKER");

    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    expect(screen.queryByRole("button", { name: "Novo pedido" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
  });

  it("mostra a mensagem mapeada quando a busca falha", async () => {
    vi.mocked(listOrders).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado."));

    render(<OrderListPage />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Seu perfil não tem permissão para esta ação."),
    );
  });
});
