import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { createCustomerAddress, listCustomerAddresses, updateCustomerAddress } from "../api/customerAddressesApi";
import { lookupAddressByCep } from "../api/customersApi";
import type { CustomerAddress } from "../types";
import { CustomerAddressPanel } from "./CustomerAddressPanel";

vi.mock("../../auth/hooks/useAuth");
vi.mock("../api/customerAddressesApi");
vi.mock("../api/customersApi");
const address: CustomerAddress = { id: "a1", customerId: "c1", label: "Filial", address: "Rua antiga, 5", city: "Campinas", state: "SP", postalCode: "13000000", active: true, isPrimary: false, createdAt: "2026-10-08T00:00:00Z" };
const onChanged = vi.fn().mockResolvedValue(undefined);
function show() { return render(<CustomerAddressPanel customerId="c1" onChanged={onChanged} />); }

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user: { id: "u1", name: "Gestor", email: "manager@example.test", role: "LOGISTICS_MANAGER", active: true, createdAt: "2026-10-08T00:00:00Z" }, status: "authenticated", login: vi.fn(), logout: vi.fn() });
  vi.mocked(listCustomerAddresses).mockResolvedValue({ items: [address], total: 1, page: 1, pageSize: 20, totalPages: 1 });
  vi.mocked(updateCustomerAddress).mockResolvedValue(address);
  vi.mocked(createCustomerAddress).mockResolvedValue(address);
});

describe("endereços de cliente", () => {
  it("permite promover, arquivar, editar e filtrar sem excluir registros", async () => {
    show();
    await screen.findByText("Rua antiga, 5");
    fireEvent.click(screen.getByRole("button", { name: "Tornar principal" }));
    await waitFor(() => expect(updateCustomerAddress).toHaveBeenCalledWith("c1", "a1", { isPrimary: true }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Arquivar endereço" }));
    await waitFor(() => expect(updateCustomerAddress).toHaveBeenCalledWith("c1", "a1", { active: false }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(2));
    fireEvent.change(screen.getByLabelText("Filtrar cadastros por arquivamento"), { target: { value: "archived" } });
    await waitFor(() => expect(listCustomerAddresses).toHaveBeenLastCalledWith("c1", expect.objectContaining({ archiveStatus: "archived" })));
    fireEvent.click(screen.getByRole("button", { name: "Editar endereço" }));
    fireEvent.change(screen.getByLabelText("ENDEREÇO"), { target: { value: "Rua corrigida, 7" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar endereço" }));
    await waitFor(() => expect(updateCustomerAddress).toHaveBeenCalledWith("c1", "a1", expect.objectContaining({ address: "Rua corrigida, 7", postalCode: "13000000" })));
  });
  it("cria endereço com preenchimento por CEP e principal", async () => {
    vi.mocked(lookupAddressByCep).mockResolvedValue({ cep: "18000000", street: "Rua preenchida", city: "Sorocaba", state: "SP", neighborhood: "Centro", complement: "" });
    show();
    await screen.findByText("Rua antiga, 5");
    fireEvent.click(screen.getByRole("button", { name: "Novo endereço" }));
    fireEvent.change(screen.getByLabelText("CEP (OPCIONAL)"), { target: { value: "18000000" } });
    await waitFor(() => expect(screen.getByLabelText("CIDADE")).toHaveValue("Sorocaba"));
    fireEvent.change(screen.getByLabelText("ENDEREÇO"), { target: { value: "Rua preenchida, 10" } });
    fireEvent.click(screen.getByLabelText("Endereço principal"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar endereço" }));
    await waitFor(() => expect(createCustomerAddress).toHaveBeenCalledWith("c1", expect.objectContaining({ city: "Sorocaba", postalCode: "18000000", isPrimary: true, address: "Rua preenchida, 10" })));
  });
  it("reativa preservando identidade", async () => {
    vi.mocked(listCustomerAddresses).mockResolvedValue({ items: [{ ...address, active: false }], total: 1, page: 1, pageSize: 20, totalPages: 1 });
    show();
    fireEvent.click(await screen.findByRole("button", { name: "Reativar endereço" }));
    await waitFor(() => expect(updateCustomerAddress).toHaveBeenCalledWith("c1", "a1", { active: true }));
  });
  it("apresenta erro de ação sem fechar a lista", async () => {
    vi.mocked(updateCustomerAddress).mockRejectedValue(new ApiError("ERROR", "Falha ao arquivar"));
    show();
    fireEvent.click(await screen.findByRole("button", { name: "Arquivar endereço" }));
    expect(await screen.findByText("Falha ao arquivar")).toBeInTheDocument();
    expect(screen.getByText("Rua antiga, 5")).toBeInTheDocument();
    expect(onChanged).not.toHaveBeenCalled();
  });
});
