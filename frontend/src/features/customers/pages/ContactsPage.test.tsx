import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listDrivers } from "../../drivers/api/driversApi";
import { listCustomers } from "../api/customersApi";
import { ContactsPage } from "./ContactsPage";

vi.mock("../api/customersApi");
vi.mock("../../drivers/api/driversApi");
vi.mock("../../auth/hooks/useAuth");

const CUSTOMER = {
  id: "c1",
  name: "Distribuidora Aurora",
  document: "12.345.678/0001-90",
  phone: "(11) 90000-0000",
  address: "Rua das Palmeiras, 120",
  city: "Campinas",
  state: "SP",
  notes: "Recebe carga só até as 16h",
  createdAt: "2026-08-01T12:00:00Z",
};

const DRIVER = {
  id: "d1",
  name: "Carlos Pereira",
  document: "123.456.789-00",
  phone: "(11) 91111-1111",
  licenseNumber: "01234567890",
  licenseCategory: "E",
  active: true,
  createdAt: "2026-08-01T12:00:00Z",
};

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

describe("ContactsPage", () => {
  beforeEach(() => {
    vi.mocked(listCustomers).mockReset().mockResolvedValue([CUSTOMER]);
    vi.mocked(listDrivers).mockReset().mockResolvedValue([DRIVER]);
    mockRole("LOGISTICS_MANAGER");
  });

  it("abre em Clientes e não busca motoristas antes de precisar", async () => {
    render(<ContactsPage />);

    expect(await screen.findByText("Distribuidora Aurora")).toBeInTheDocument();
    expect(listDrivers).not.toHaveBeenCalled();
  });

  it("troca para a aba de motoristas", async () => {
    render(<ContactsPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.click(screen.getByRole("tab", { name: "Motoristas" }));

    expect(await screen.findByText("Carlos Pereira")).toBeInTheDocument();
    expect(screen.queryByText("Distribuidora Aurora")).not.toBeInTheDocument();
  });

  it("marca a aba ativa para leitores de tela", async () => {
    render(<ContactsPage />);
    await screen.findByText("Distribuidora Aurora");

    expect(screen.getByRole("tab", { name: "Clientes" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Motoristas" })).toHaveAttribute("aria-selected", "false");
  });

  it("busca cliente por cidade sem chamar o backend de novo", async () => {
    vi.mocked(listCustomers).mockResolvedValue([
      CUSTOMER,
      { ...CUSTOMER, id: "c2", name: "Mercado Central", city: "Sorocaba" },
    ]);

    render(<ContactsPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.change(screen.getByLabelText("Buscar cliente por nome, documento ou cidade"), {
      target: { value: "sorocaba" },
    });

    expect(screen.queryByText("Distribuidora Aurora")).not.toBeInTheDocument();
    expect(screen.getByText("Mercado Central")).toBeInTheDocument();
    expect(listCustomers).toHaveBeenCalledOnce();
  });

  it("filtra motoristas por status", async () => {
    vi.mocked(listDrivers).mockResolvedValue([DRIVER, { ...DRIVER, id: "d2", name: "Rita Alves", active: false }]);

    render(<ContactsPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Motoristas" }));
    await screen.findByText("Carlos Pereira");

    fireEvent.change(screen.getByLabelText("Filtrar motoristas por status"), {
      target: { value: "inactive" },
    });

    expect(screen.queryByText("Carlos Pereira")).not.toBeInTheDocument();
    expect(screen.getByText("Rita Alves")).toBeInTheDocument();
  });

  it("esconde as ações de gestão para o ADMIN, que só lê", async () => {
    mockRole("ADMIN");

    render(<ContactsPage />);
    await screen.findByText("Distribuidora Aurora");

    expect(screen.queryByRole("button", { name: "+ Novo cliente" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
  });

  it("mostra a mensagem mapeada quando a busca de clientes falha", async () => {
    vi.mocked(listCustomers).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado."));

    render(<ContactsPage />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Seu perfil não tem permissão para ver ou alterar clientes.",
      ),
    );
  });
});
