import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import type { Role } from "../../auth/types";
import { listTrips } from "../api/tripsApi";
import type { TripListItem } from "../types";
import { TripListPage } from "./TripListPage";

vi.mock("../api/tripsApi");
vi.mock("../../auth/hooks/useAuth");

function trip(overrides: Partial<TripListItem> = {}): TripListItem {
  return {
    id: "tp1",
    loadPlanId: "lp1",
    driverId: "d1",
    status: "SCHEDULED",
    startedAt: null,
    finishedAt: null,
    createdAt: "2026-10-20T10:00:00Z",
    deliveryCount: 3,
    ...overrides,
  };
}

function page(items: TripListItem[]) {
  return { items, page: 1, pageSize: 20, total: items.length, totalPages: 1 };
}

function mockRole(role: Role) {
  vi.mocked(useAuth).mockReturnValue({
    status: "authenticated",
    user: {
      id: "u1",
      name: "Ana",
      email: "ana@empresa.test",
      role,
      active: true,
      createdAt: "2026-08-01T00:00:00Z",
    },
    login: vi.fn(),
    logout: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
}

function renderPage() {
  return render(
    <MemoryRouter>
      <TripListPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockRole("LOGISTICS_MANAGER");
  vi.mocked(listTrips).mockReset().mockResolvedValue(page([trip()]));
});

describe("TripListPage", () => {
  it("leva da lista ao detalhe sem exigir que alguém conheça o UUID", async () => {
    // É a razão de a OC93 existir: até aqui só se abria uma viagem pelo plano
    // que a gerou ou digitando o id na barra de endereço.
    vi.mocked(listTrips).mockResolvedValue(page([trip({ id: "tp-99" })]));

    renderPage();

    expect(await screen.findByRole("link", { name: "Abrir" })).toHaveAttribute(
      "href",
      "/trips/tp-99",
    );
  });

  it("mostra situação e número de paradas de cada viagem", async () => {
    vi.mocked(listTrips).mockResolvedValue(
      page([trip({ status: "IN_ROUTE", deliveryCount: 1 })]),
    );

    renderPage();

    const linha = (await screen.findByText("Em rota")).closest("tr") as HTMLElement;
    expect(within(linha).getByText("1 parada")).toBeInTheDocument();
  });

  it("NÃO filtra por motorista: o recorte é do backend", async () => {
    // Repetir o recorte aqui duplicaria no cliente uma regra de acesso que já é
    // aplicada onde importa — e esconderia do gestor viagens que ele pode ver.
    mockRole("DRIVER");
    vi.mocked(listTrips).mockResolvedValue(
      page([trip({ id: "a", driverId: "outro" }), trip({ id: "b", driverId: "u1" })]),
    );

    renderPage();

    await waitFor(() => expect(screen.getAllByRole("link", { name: "Abrir" })).toHaveLength(2));
    expect(vi.mocked(listTrips).mock.calls[0][0]).not.toHaveProperty("driverId");
  });

  it("fala com o motorista na língua dele quando não há viagem", async () => {
    mockRole("DRIVER");
    vi.mocked(listTrips).mockResolvedValue(page([]));

    renderPage();

    expect(await screen.findByText(/não tem viagens atribuídas/)).toBeInTheDocument();
  });

  it("ao gestor sem viagens, explica de onde elas nascem", async () => {
    vi.mocked(listTrips).mockResolvedValue(page([]));

    renderPage();

    expect(await screen.findByText(/plano de carga aprovado/)).toBeInTheDocument();
  });

  it("oferece nova tentativa quando a consulta falha", async () => {
    vi.mocked(listTrips).mockRejectedValue(new ApiError("NETWORK_ERROR", "sem rede"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(/conexão/i);
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("a tabela rola em tela estreita sem empurrar a página", async () => {
    renderPage();

    expect(await screen.findByRole("region", { name: "Viagens" })).toHaveClass(
      "trip-list-scroll",
    );
  });
  it("consulta no servidor viagens interrompidas sem filtrar apenas pagina corrente", async () => {
    renderPage();
    await screen.findByRole("link", { name: "Abrir" });
    const select = screen.getByRole("combobox", { name: "Filtrar viagens por situação" });
    fireEvent.change(select, { target: { value: "INTERRUPTED" } });
    await waitFor(() => expect(listTrips).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: "INTERRUPTED", page: 1 }),
    ));
  });

  it("consulta no servidor identificador da viagem ao buscar", async () => {
    renderPage();
    await screen.findByRole("link", { name: "Abrir" });
    fireEvent.change(screen.getByRole("textbox", { name: "Buscar viagem por identificador" }), {
      target: { value: "abc" },
    });
    await waitFor(() => expect(listTrips).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "abc", page: 1 }),
    ));
  });

});
