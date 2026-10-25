import { MemoryRouter } from "react-router-dom";
import { fireEvent, render as renderView, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import type { Page } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listTrucks } from "../api/trucksApi";
import type { Truck } from "../types";
import { TruckListPage } from "./TruckListPage";

function render(ui: React.ReactElement) { return renderView(<MemoryRouter>{ui}</MemoryRouter>); }

vi.mock("../api/trucksApi");
vi.mock("../../auth/hooks/useAuth");

const TRUCKS: Truck[] = [
  {
    id: "1",
    plate: "ABC1D23",
    model: "Baú médio",
    internalWidthCm: 240,
    internalHeightCm: 260,
    internalLengthCm: 600,
    maxWeightKg: 8000,
    active: true,
    createdAt: "2026-08-01T12:00:00Z",
  },
  {
    id: "2",
    plate: "QRT2B88",
    model: "Baú reforçado",
    internalWidthCm: 245,
    internalHeightCm: 270,
    internalLengthCm: 750,
    maxWeightKg: 10000,
    active: false,
    createdAt: "2026-08-02T12:00:00Z",
  },
];

function makePage(
  items: Truck[],
  page = 1,
  totalPages = items.length === 0 ? 0 : 1,
): Page<Truck> {
  return {
    items,
    page,
    pageSize: 20,
    total: totalPages <= 1 ? items.length : 21,
    totalPages,
  };
}

function mockRole(role: "LOGISTICS_MANAGER" | "ADMIN") {
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

describe("TruckListPage", () => {
  beforeEach(() => {
    vi.mocked(listTrucks).mockReset();
    mockRole("LOGISTICS_MANAGER");
  });

  it("lista os caminhões retornados pelo backend", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));

    render(<TruckListPage />);

    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
    expect(screen.getByText("QRT2B88")).toBeInTheDocument();
    expect(screen.getByText("Ativo")).toBeInTheDocument();
    expect(screen.getByText("Arquivado")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Caminhões cadastrados" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Volume interno" })).toBeInTheDocument();
  });

  it("organiza as ações em grupo separado do peso máximo de cada caminhão", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));
    mockRole("ADMIN");
    render(<TruckListPage />);

    const trigger = await screen.findByLabelText("Ações do caminhão ABC1D23");
    fireEvent.click(trigger);
    const actions = trigger.closest("details")!;
    expect(within(actions).getByRole("button", { name: "Documentos" })).toBeInTheDocument();
    expect(within(actions).getByRole("button", { name: "Manutenções" })).toBeInTheDocument();
    expect(within(actions).getByRole("button", { name: "Arquivar" })).toBeInTheDocument();
    expect(within(actions).getByRole("button", { name: "Editar" })).toBeInTheDocument();
    expect(within(actions).getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Documentos", "Manutenções", "Editar", "Arquivar",
    ]);
    const card = actions.closest(".truck-card");
    expect(card?.querySelector(".truck-card-weight")).toHaveTextContent("8.000 kg");
    expect(actions.contains(card?.querySelector(".truck-card-weight") ?? null)).toBe(false);
  });

  it("filtra por placa ou modelo consultando o servidor", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));

    render(<TruckListPage />);
    await screen.findByText("ABC1D23");

    vi.mocked(listTrucks).mockResolvedValue(makePage([TRUCKS[1]]));
    fireEvent.change(screen.getByLabelText("Buscar por placa ou modelo"), {
      target: { value: "reforçado" },
    });

    await waitFor(() => expect(listTrucks).toHaveBeenLastCalledWith(expect.objectContaining({ search: "reforçado" })));
    await screen.findByText("QRT2B88");

    expect(screen.queryByText("ABC1D23")).not.toBeInTheDocument();
    expect(screen.getByText("QRT2B88")).toBeInTheDocument();
    expect(listTrucks).toHaveBeenLastCalledWith(expect.objectContaining({ search: "reforçado", page: 1 }));
  });

  it("filtra por status", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));

    render(<TruckListPage />);
    await screen.findByText("ABC1D23");

    vi.mocked(listTrucks).mockResolvedValue(makePage([TRUCKS[1]]));
    fireEvent.change(screen.getByLabelText("Filtrar cadastros por arquivamento"), { target: { value: "archived" } });

    await waitFor(() => expect(listTrucks).toHaveBeenLastCalledWith({ page: 1, pageSize: 20, archiveStatus: "archived", search: "" }));
    expect(await screen.findByText("QRT2B88")).toBeInTheDocument();
    expect(screen.queryByText("ABC1D23")).not.toBeInTheDocument();
  });

  it("permite ao ADMIN gerenciar caminhões", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));
    mockRole("ADMIN");

    render(<TruckListPage />);
    await screen.findByText("ABC1D23");

    expect(screen.getByRole("button", { name: "Novo caminhão" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Editar" }).length).toBeGreaterThan(0);
  });

  it("abre o formulário de cadastro para o gestor de logística", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));

    render(<TruckListPage />);
    await screen.findByText("ABC1D23");

    fireEvent.click(screen.getByRole("button", { name: "Novo caminhão" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Novo caminhão" })).toBeInTheDocument();
  });

  it("mostra o estado vazio quando não há caminhões", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage([]));

    render(<TruckListPage />);

    expect(await screen.findByText("Nenhum caminhão cadastrado ainda.")).toBeInTheDocument();
  });

  it("mostra a mensagem mapeada quando a busca falha", async () => {
    vi.mocked(listTrucks).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado."));

    render(<TruckListPage />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Seu perfil não tem permissão para esta ação."),
    );
  });

  it("navega entre páginas usando os metadados do backend", async () => {
    vi.mocked(listTrucks)
      .mockResolvedValueOnce(makePage([TRUCKS[0]], 1, 2))
      .mockResolvedValueOnce(makePage([TRUCKS[1]], 2, 2));

    render(<TruckListPage />);

    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
    expect(screen.getByText("Página 1 de 2")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));

    expect(await screen.findByText("QRT2B88")).toBeInTheDocument();
    expect(screen.getByText("Página 2 de 2")).toBeInTheDocument();
    expect(listTrucks).toHaveBeenLastCalledWith({ page: 2, pageSize: 20, archiveStatus: "active", search: "" });
  });
});
