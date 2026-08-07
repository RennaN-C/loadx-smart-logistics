import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listProducts } from "../api/productsApi";
import type { Product } from "../types";
import { ProductListPage } from "./ProductListPage";

vi.mock("../api/productsApi");
vi.mock("../../auth/hooks/useAuth");

const PRODUCTS: Product[] = [
  {
    id: "1",
    code: "CX-100",
    name: "Caixa média",
    description: "Papelão reforçado",
    widthCm: 40,
    heightCm: 30,
    lengthCm: 60,
    weightKg: 12.5,
    fragile: false,
    stackable: true,
    rotationAllowed: true,
    createdAt: "2026-08-01T12:00:00Z",
  },
  {
    id: "2",
    code: "VD-200",
    name: "Engradado de vidro",
    description: null,
    widthCm: 30,
    heightCm: 40,
    lengthCm: 30,
    weightKg: 18,
    fragile: true,
    stackable: false,
    rotationAllowed: false,
    createdAt: "2026-08-02T12:00:00Z",
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

describe("ProductListPage", () => {
  beforeEach(() => {
    vi.mocked(listProducts).mockReset();
    mockRole("LOGISTICS_MANAGER");
  });

  it("lista os produtos retornados pelo backend", async () => {
    vi.mocked(listProducts).mockResolvedValue(makePage(PRODUCTS));

    render(<ProductListPage />);

    expect(await screen.findByText("CX-100")).toBeInTheDocument();
    expect(screen.getByText("VD-200")).toBeInTheDocument();
  });

  it("mostra só as restrições reais de cada produto", async () => {
    vi.mocked(listProducts).mockResolvedValue(makePage(PRODUCTS));

    render(<ProductListPage />);
    await screen.findByText("CX-100");

    expect(screen.getByText("Sem restrições")).toBeInTheDocument();
    expect(screen.getByText("Frágil")).toBeInTheDocument();
    expect(screen.getByText("Não empilhável")).toBeInTheDocument();
    expect(screen.getByText("Sem rotação")).toBeInTheDocument();
  });

  it("filtra por código ou nome sem chamar o backend de novo", async () => {
    vi.mocked(listProducts).mockResolvedValue(makePage(PRODUCTS));

    render(<ProductListPage />);
    await screen.findByText("CX-100");

    fireEvent.change(screen.getByLabelText("Buscar por código ou nome"), {
      target: { value: "vidro" },
    });

    expect(screen.queryByText("CX-100")).not.toBeInTheDocument();
    expect(screen.getByText("VD-200")).toBeInTheDocument();
    expect(listProducts).toHaveBeenCalledOnce();
  });

  it("filtra por restrição", async () => {
    vi.mocked(listProducts).mockResolvedValue(makePage(PRODUCTS));

    render(<ProductListPage />);
    await screen.findByText("CX-100");

    fireEvent.change(screen.getByLabelText("Filtrar por restrição"), {
      target: { value: "restricted" },
    });

    expect(screen.queryByText("CX-100")).not.toBeInTheDocument();
    expect(screen.getByText("VD-200")).toBeInTheDocument();
  });

  it("esconde as ações de gestão para quem só tem leitura", async () => {
    vi.mocked(listProducts).mockResolvedValue(makePage(PRODUCTS));
    mockRole("CHECKER");

    render(<ProductListPage />);
    await screen.findByText("CX-100");

    expect(screen.queryByRole("button", { name: "+ Novo produto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
  });

  it("mostra o estado vazio quando não há produtos", async () => {
    vi.mocked(listProducts).mockResolvedValue(makePage([]));

    render(<ProductListPage />);

    expect(await screen.findByText("Nenhum produto cadastrado ainda.")).toBeInTheDocument();
  });

  it("mostra a mensagem mapeada quando a busca falha", async () => {
    vi.mocked(listProducts).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado."));

    render(<ProductListPage />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Seu perfil não tem permissão para esta ação."),
    );
  });
});
