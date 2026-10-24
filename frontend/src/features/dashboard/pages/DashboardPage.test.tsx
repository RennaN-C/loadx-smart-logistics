import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

import { getOperationalIndicators } from "../../operations/api/operationalIndicatorsApi";
vi.mock("../../operations/api/operationalIndicatorsApi");
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

function mockRole(role: "ADMIN" | "LOGISTICS_MANAGER" | "CHECKER" | "DRIVER") {
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
    updateUser: vi.fn(),
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
    vi.mocked(getOperationalIndicators).mockResolvedValue({ fleet: { period: "CURRENT_SNAPSHOT", total: 6, active: 5, inactive: 1, available: 4, unavailable: 2, withOperationConflict: 1 }, trips: { period: "ALL_TIME", total: 9, scheduled: 3, inRoute: 2, finished: 4 }, deliveries: { period: "ALL_TIME", total: 20, pending: 7, inDelivery: 3, delivered: 10 }, occurrences: { period: "ALL_TIME", total: 2 } });
    vi.mocked(listTrucks).mockResolvedValue(pageWithTotal(4));
    vi.mocked(listProducts).mockResolvedValue({ ...makePage([{
      id: "p1", code: "CX-100", name: "Caixa média", description: null,
      widthCm: 40, heightCm: 30, lengthCm: 60, weightKg: 12.5,
      fragile: false, stackable: true, rotationAllowed: true, active: true,
      createdAt: "2026-08-01T00:00:00Z",
    }]), total: 12 });
    vi.mocked(listDrivers).mockResolvedValue(pageWithTotal(3));
    vi.mocked(listCustomers).mockResolvedValue(
      makePage([
        { id: "c1", name: "Distribuidora Aurora", active: true, city: "Campinas", state: "SP", createdAt: "2026-08-01T00:00:00Z" },
      ]),
    );
    vi.mocked(listOrders).mockResolvedValue({ ...makePage([ORDER]), total: 27 });
  });

  it("conta pelo total do envelope, sem baixar a coleção inteira", async () => {
    mockRole("CHECKER");
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
    expect(screen.getByText(/3 linhas/)).toBeInTheDocument();
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
    mockRole("CHECKER");
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

  it("mostra o acesso ao planejamento para ADMIN", async () => {
    mockRole("ADMIN");
    renderPage();
    expect(await screen.findByRole("link", { name: "Planejar carga" })).toHaveAttribute(
      "href",
      "/planning?tab=new",
    );
  });

  it("só oferece planejar carga para quem pode", async () => {
    mockRole("CHECKER");

    renderPage();
    await screen.findByText("4");

    expect(screen.queryByRole("link", { name: "Planejar carga" })).not.toBeInTheDocument();
  });
  it.each(["ADMIN", "LOGISTICS_MANAGER"] as const)("%s recebe indicadores reais sem duplicar o total de caminhões", async (role) => {
    mockRole(role); renderPage();
    await screen.findByRole("heading", { name: "Situação das viagens" });
    expect(getOperationalIndicators).toHaveBeenCalledOnce();
    expect(listTrucks).not.toHaveBeenCalled();
    expect(screen.getByRole("link", { name: /Caminhões disponíveis/ })).toHaveAttribute("href", "/trucks?tab=availability");
    expect(screen.getByRole("link", { name: "Abrir pedido o1" })).toHaveAttribute("href", "/orders?order=o1");
    expect(screen.getByRole("img", { name: "27 pedidos e 20 entregas" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cargas disponíveis" })).toBeInTheDocument();
    expect(screen.getByText("CX-100")).toBeInTheDocument();
  });

  it("falha operacional preserva pedidos recentes e permite nova tentativa", async () => {
    vi.mocked(getOperationalIndicators).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "sem rede"));
    renderPage();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(await screen.findByText("Distribuidora Aurora")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await screen.findByRole("heading", { name: "Situação das viagens" });
    expect(getOperationalIndicators).toHaveBeenCalledTimes(2);
  });

  it("conferente não consulta indicadores globais nem dados pessoais", async () => {
    mockRole("CHECKER"); renderPage();
    await screen.findByText("4");
    expect(getOperationalIndicators).not.toHaveBeenCalled();
    expect(listCustomers).not.toHaveBeenCalled();
    expect(listDrivers).not.toHaveBeenCalled();
  });

});

it("motorista não dispara consultas aos cadastros restritos ao abrir painel", async () => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ status: "authenticated", user: { id: "u1", name: "Motorista de teste", email: "d@example.test", role: "DRIVER", active: true, createdAt: "2026-01-01T00:00:00Z" }, login: vi.fn(), updateUser: vi.fn(), logout: vi.fn() });
  vi.mocked(listTrips).mockResolvedValue(makePage([]));
  render(<MemoryRouter><DashboardPage /></MemoryRouter>);
  await screen.findByText(/Você ainda não tem viagens/);
  expect(listCustomers).not.toHaveBeenCalled();
  expect(listTrucks).not.toHaveBeenCalled();
  expect(listOrders).not.toHaveBeenCalled();
});
