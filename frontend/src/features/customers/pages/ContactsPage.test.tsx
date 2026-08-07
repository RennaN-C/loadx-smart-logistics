import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makePage } from "../../../tests/makePage";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { getDriver, listDrivers } from "../../drivers/api/driversApi";
import { getCustomer, listCustomers } from "../api/customersApi";
import { ContactsPage } from "./ContactsPage";

vi.mock("../api/customersApi");
vi.mock("../../drivers/api/driversApi");
vi.mock("../../auth/hooks/useAuth");

/** Resumo devolvido pela listagem: sem documento, telefone, endereço nem notas. */
const CUSTOMER_ITEM = {
  id: "c1",
  name: "Distribuidora Aurora",
  city: "Campinas",
  state: "SP",
  createdAt: "2026-08-01T12:00:00Z",
};

const CUSTOMER_FULL = {
  ...CUSTOMER_ITEM,
  document: "12.345.678/0001-90",
  phone: "(11) 90000-0000",
  address: "Rua das Palmeiras, 120",
  notes: "Recebe carga só até as 16h",
};

const DRIVER_ITEM = {
  id: "d1",
  name: "Carlos Pereira",
  licenseCategory: "E",
  active: true,
  createdAt: "2026-08-01T12:00:00Z",
};

const DRIVER_FULL = {
  ...DRIVER_ITEM,
  document: "123.456.789-00",
  phone: "(11) 91111-1111",
  licenseNumber: "01234567890",
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
    vi.mocked(listCustomers).mockReset().mockResolvedValue(makePage([CUSTOMER_ITEM]));
    vi.mocked(listDrivers).mockReset().mockResolvedValue(makePage([DRIVER_ITEM]));
    vi.mocked(getCustomer).mockReset().mockResolvedValue(CUSTOMER_FULL);
    vi.mocked(getDriver).mockReset().mockResolvedValue(DRIVER_FULL);
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

  it("não expõe dado pessoal no card, porque a listagem não traz", async () => {
    render(<ContactsPage />);
    await screen.findByText("Distribuidora Aurora");

    expect(screen.queryByText("12.345.678/0001-90")).not.toBeInTheDocument();
    expect(screen.queryByText("Rua das Palmeiras, 120")).not.toBeInTheDocument();
    expect(screen.getByText("Campinas · SP")).toBeInTheDocument();
  });

  it("busca o cliente completo antes de abrir a edição", async () => {
    render(<ContactsPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));

    await waitFor(() => expect(getCustomer).toHaveBeenCalledWith("c1"));
    // só depois do detalhe é que os campos pessoais aparecem no formulário
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("DOCUMENTO")).toHaveValue("12.345.678/0001-90");
  });

  it("avisa quando não consegue carregar o detalhe para edição", async () => {
    vi.mocked(getCustomer).mockRejectedValue(new ApiError("CUSTOMER_NOT_FOUND", "x"));

    render(<ContactsPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.click(screen.getByRole("button", { name: "Editar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Este cliente não foi encontrado.");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("busca cliente por cidade sem chamar o backend de novo", async () => {
    vi.mocked(listCustomers).mockResolvedValue(
      makePage([CUSTOMER_ITEM, { ...CUSTOMER_ITEM, id: "c2", name: "Mercado Central", city: "Sorocaba" }]),
    );

    render(<ContactsPage />);
    await screen.findByText("Distribuidora Aurora");

    fireEvent.change(screen.getByLabelText("Buscar cliente por nome ou cidade"), {
      target: { value: "sorocaba" },
    });

    expect(screen.queryByText("Distribuidora Aurora")).not.toBeInTheDocument();
    expect(screen.getByText("Mercado Central")).toBeInTheDocument();
    expect(listCustomers).toHaveBeenCalledOnce();
  });

  it("filtra motoristas por status", async () => {
    vi.mocked(listDrivers).mockResolvedValue(
      makePage([DRIVER_ITEM, { ...DRIVER_ITEM, id: "d2", name: "Rita Alves", active: false }]),
    );

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
