import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listDrivers } from "../../drivers/api/driversApi";
import { listOrders } from "../../orders/api/ordersApi";
import { listProducts } from "../../products/api/productsApi";
import { listTrucks } from "../../trucks/api/trucksApi";
import { DashboardPage } from "./DashboardPage";

vi.mock("../../trucks/api/trucksApi");
vi.mock("../../products/api/productsApi");
vi.mock("../../customers/api/customersApi");
vi.mock("../../drivers/api/driversApi");
vi.mock("../../orders/api/ordersApi");
vi.mock("../../auth/hooks/useAuth");

/** O contador usa `total`, não o tamanho de `items`. */
function pageWithTotal(total: number) {
  return { items: [], page: 1, pageSize: 1, total, totalPages: total };
}

const ORDER = {
  id: "o1",
  customerId: "c1",
  status: "READY" as const,
  priority: "HIGH",
  expectedDeliveryAt: null,
  createdAt: "2026-08-05T12:00:00Z",
  itemCount: 3,
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

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockRole("LOGISTICS_MANAGER");
    vi.mocked(listTrucks).mockResolvedValue(pageWithTotal(4));
    vi.mocked(listProducts).mockResolvedValue(pageWithTotal(12));
    vi.mocked(listDrivers).mockResolvedValue(pageWithTotal(3));
    vi.mocked(listCustomers).mockResolvedValue(
      makePage([
        { id: "c1", name: "Distribuidora Aurora", city: "Campinas", state: "SP", createdAt: "2026-08-01T00:00:00Z" },
      ]),
    );
    vi.mocked(listOrders).mockResolvedValue({ ...makePage([ORDER]), total: 27 });
  });

  it("conta pelo total do envelope, sem baixar a coleção inteira", async () => {
    renderPage();

    expect(await screen.findByText("4")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("27")).toBeInTheDocument();
    // page_size=1: o número vem do total, não dos itens
    expect(listTrucks).toHaveBeenCalledWith({ pageSize: 1 });
  });

  it("lista os pedidos mais recentes resolvendo o nome do cliente", async () => {
    renderPage();

    expect(await screen.findByText("Distribuidora Aurora")).toBeInTheDocument();
    expect(screen.getByText("Pronto")).toBeInTheDocument();
    expect(screen.getByText(/3 itens/)).toBeInTheDocument();
    expect(screen.getByText(/Alta/)).toBeInTheDocument();
  });

  it("não busca dado pessoal para quem não pode ler", async () => {
    mockRole("CHECKER");

    renderPage();
    await screen.findByText("4");

    expect(listDrivers).not.toHaveBeenCalled();
    expect(screen.queryByText("MOTORISTAS")).not.toBeInTheDocument();
  });

  it("um recurso indisponível não derruba o painel inteiro", async () => {
    vi.mocked(listProducts).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "x"));

    renderPage();

    // caminhões continuam contando; produtos viram "—"
    expect(await screen.findByText("4")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/aparecem como/)).toBeInTheDocument());
  });

  it("mostra o estado vazio quando não há pedidos", async () => {
    vi.mocked(listOrders).mockResolvedValue({ ...makePage([]), total: 0 });

    renderPage();

    expect(await screen.findByText("Nenhum pedido cadastrado ainda.")).toBeInTheDocument();
  });

  it("só oferece planejar carga para quem pode", async () => {
    mockRole("CHECKER");

    renderPage();
    await screen.findByText("4");

    expect(screen.queryByRole("link", { name: "Planejar carga" })).not.toBeInTheDocument();
  });
});
