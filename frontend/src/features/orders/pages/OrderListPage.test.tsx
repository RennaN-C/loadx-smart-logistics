import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listProducts } from "../../products/api/productsApi";
import { listOrders } from "../api/ordersApi";
import type { Order } from "../types";
import { OrderListPage } from "./OrderListPage";

vi.mock("../api/ordersApi");
vi.mock("../../customers/api/customersApi");
vi.mock("../../products/api/productsApi");
vi.mock("../../auth/hooks/useAuth");

const ORDERS: Order[] = [
  {
    id: "o1",
    customerId: "c1",
    status: "DRAFT",
    priority: "NORMAL",
    deliveryAddress: "Av. Brasil, 500",
    expectedDeliveryAt: null,
    createdAt: "2026-08-01T00:00:00Z",
    items: [
      { id: "i1", orderId: "o1", productId: "p1", quantity: 4, deliverySequence: 2 },
      { id: "i2", orderId: "o1", productId: "p2", quantity: 1, deliverySequence: 1 },
    ],
  },
  {
    id: "o2",
    customerId: "c2",
    status: "DELIVERED",
    priority: "URGENT",
    deliveryAddress: "Rua das Flores, 10",
    expectedDeliveryAt: null,
    createdAt: "2026-08-02T00:00:00Z",
    items: [{ id: "i3", orderId: "o2", productId: "p1", quantity: 2, deliverySequence: 1 }],
  },
];

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
    vi.mocked(listOrders).mockReset().mockResolvedValue(ORDERS);
    vi.mocked(listCustomers)
      .mockReset()
      .mockResolvedValue([
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
      ]);
    vi.mocked(listProducts)
      .mockReset()
      .mockResolvedValue([
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
      ]);
    mockRole("LOGISTICS_MANAGER");
  });

  it("resolve o nome do cliente e o rótulo do produto a partir dos ids", async () => {
    render(<OrderListPage />);

    expect(await screen.findByText("Distribuidora Aurora")).toBeInTheDocument();
    expect(screen.getAllByText("CX-100 — Caixa média").length).toBeGreaterThan(0);
  });

  it("avisa quando o id referenciado não está mais nas listas", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    // c2 e p2 não existem nos mocks
    expect(screen.getByText("Cliente não encontrado")).toBeInTheDocument();
    expect(screen.getByText("Produto não encontrado")).toBeInTheDocument();
  });

  it("ordena os itens do card pela sequência de entrega, não pela ordem da API", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    const sequences = [...document.querySelectorAll(".order-card-seq")].map((el) => el.textContent);

    expect(sequences.slice(0, 2)).toEqual(["1", "2"]);
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
    expect(screen.getByText("Rua das Flores, 10")).toBeInTheDocument();
  });

  it("busca por cliente ou endereço sem chamar o backend de novo", async () => {
    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.change(screen.getByLabelText("Buscar por cliente ou endereço"), {
      target: { value: "flores" },
    });

    expect(screen.queryByText("Distribuidora Aurora")).not.toBeInTheDocument();
    expect(screen.getByText("Rua das Flores, 10")).toBeInTheDocument();
    expect(listOrders).toHaveBeenCalledOnce();
  });

  it("esconde as ações de gestão para quem só tem leitura", async () => {
    mockRole("CHECKER");

    render(<OrderListPage />);
    await screen.findByText("Distribuidora Aurora");

    expect(screen.queryByRole("button", { name: "+ Novo pedido" })).not.toBeInTheDocument();
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
