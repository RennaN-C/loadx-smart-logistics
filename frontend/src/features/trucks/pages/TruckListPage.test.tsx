import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import type { Page } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listTrucks } from "../api/trucksApi";
import type { Truck } from "../types";
import { TruckListPage } from "./TruckListPage";

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
    expect(screen.getByText("Inativo")).toBeInTheDocument();
  });

  it("filtra por placa ou modelo sem chamar o backend de novo", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));

    render(<TruckListPage />);
    await screen.findByText("ABC1D23");

    fireEvent.change(screen.getByLabelText("Buscar por placa ou modelo"), {
      target: { value: "reforçado" },
    });

    expect(screen.queryByText("ABC1D23")).not.toBeInTheDocument();
    expect(screen.getByText("QRT2B88")).toBeInTheDocument();
    expect(listTrucks).toHaveBeenCalledOnce();
  });

  it("filtra por status", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));

    render(<TruckListPage />);
    await screen.findByText("ABC1D23");

    fireEvent.change(screen.getByLabelText("Filtrar por status"), { target: { value: "inactive" } });

    expect(screen.queryByText("ABC1D23")).not.toBeInTheDocument();
    expect(screen.getByText("QRT2B88")).toBeInTheDocument();
  });

  it("esconde as ações de gestão para quem só tem leitura", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));
    mockRole("ADMIN");

    render(<TruckListPage />);
    await screen.findByText("ABC1D23");

    expect(screen.queryByRole("button", { name: "+ Novo caminhão" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
  });

  it("abre o formulário de cadastro para o gestor de logística", async () => {
    vi.mocked(listTrucks).mockResolvedValue(makePage(TRUCKS));

    render(<TruckListPage />);
    await screen.findByText("ABC1D23");

    fireEvent.click(screen.getByRole("button", { name: "+ Novo caminhão" }));

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
    expect(listTrucks).toHaveBeenLastCalledWith({ page: 2, pageSize: 20 });
  });
});
