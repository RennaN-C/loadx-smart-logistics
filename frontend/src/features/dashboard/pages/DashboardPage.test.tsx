import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listDrivers } from "../../drivers/api/driversApi";
import { listOrders } from "../../orders/api/ordersApi";
import type { OrderListItem } from "../../orders/types";
import { listProducts } from "../../products/api/productsApi";
import { listTrips } from "../../deliveries/api/tripsApi";
import type { TripListItem } from "../../deliveries/types";
import { listTrucks } from "../../trucks/api/trucksApi";
import { DashboardPage } from "./DashboardPage";

vi.mock("../../trucks/api/trucksApi");
vi.mock("../../products/api/productsApi");
vi.mock("../../customers/api/customersApi");
vi.mock("../../drivers/api/driversApi");
vi.mock("../../orders/api/ordersApi");
vi.mock("../../auth/hooks/useAuth");
vi.mock("../../deliveries/api/tripsApi");

/** O contador usa `total`, não o tamanho de `items`. */
function pageWithTotal(total: number) {
  return { items: [], page: 1, pageSize: 1, total, totalPages: total };
}

const ORDER: OrderListItem = {
  id: "o1",
  customerId: "c1",
  status: "READY",
  priority: "HIGH",
  expectedDeliveryAt: null,
  createdAt: "2026-08-05T12:00:00Z",
  itemCount: 3,
};

function mockRole(role: "LOGISTICS_MANAGER" | "CHECKER" | "DRIVER") {
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
  function trip(overrides: Partial<TripListItem> = {}): TripListItem {
    return {
      id: "tp1",
      loadPlanId: "lp1",
      driverId: "d1",
      status: "SCHEDULED",
      startedAt: null,
      finishedAt: null,
      createdAt: "2026-08-20T10:00:00Z",
      deliveryCount: 3,
      ...overrides,
    };
  }

  it("mostra ao motorista as viagens dele, não o painel de cadastros", async () => {
    // O motorista não lê caminhões, produtos, pedidos nem clientes: TODOS os
    // contadores respondem 403 para ele, e a tela abria com quatro traços.
    mockRole("DRIVER");
    vi.mocked(listTrips).mockResolvedValue(makePage([trip()]));

    renderPage();

    expect(await screen.findByText("Minhas viagens")).toBeInTheDocument();
    expect(screen.getByText("3 paradas")).toBeInTheDocument();
    expect(screen.queryByText("CAMINHÕES")).not.toBeInTheDocument();
    expect(screen.queryByText(/não puderam ser carregados/)).not.toBeInTheDocument();
  });

  it("leva o motorista para a viagem escolhida", async () => {
    mockRole("DRIVER");
    vi.mocked(listTrips).mockResolvedValue(makePage([trip({ id: "tp-99" })]));

    renderPage();

    expect(await screen.findByRole("link", { name: "Abrir" })).toHaveAttribute(
      "href",
      "/trips/tp-99",
    );
  });

  it("explica ao motorista sem viagem em vez de mostrar lista vazia", async () => {
    mockRole("DRIVER");
    vi.mocked(listTrips).mockResolvedValue(makePage([]));

    renderPage();

    expect(await screen.findByText(/ainda não tem viagens atribuídas/)).toBeInTheDocument();
  });

  it("oferece nova tentativa quando a lista de viagens falha", async () => {
    mockRole("DRIVER");
    vi.mocked(listTrips).mockRejectedValue(new ApiError("NETWORK_ERROR", "sem rede"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(/Verifique sua conexão/);
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

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
