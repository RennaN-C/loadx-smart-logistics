import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OrderListPage } from "../features/orders/pages/OrderListPage";
import { ProductListPage } from "../features/products/pages/ProductListPage";
import { TruckListPage } from "../features/trucks/pages/TruckListPage";
import { CustomerPanel } from "../features/customers/components/CustomerPanel";
import { DriverPanel } from "../features/drivers/components/DriverPanel";
import { ApiError } from "../types/api";
import { makePage } from "./makePage";

const mocks = vi.hoisted(() => ({ orders: vi.fn(), products: vi.fn(), trucks: vi.fn(), customers: vi.fn(), drivers: vi.fn() }));
vi.mock("../features/orders/api/ordersApi", () => ({ listOrders: mocks.orders, getOrder: vi.fn() }));
vi.mock("../features/products/api/productsApi", () => ({ listProducts: mocks.products }));
vi.mock("../features/trucks/api/trucksApi", () => ({ listTrucks: mocks.trucks }));
vi.mock("../features/customers/api/customersApi", () => ({ listCustomers: mocks.customers, getCustomer: vi.fn() }));
vi.mock("../features/drivers/api/driversApi", () => ({ listDrivers: mocks.drivers, getDriver: vi.fn() }));
vi.mock("../features/auth/hooks/useAuth", () => ({ useAuth: () => ({ user: { active: true, role: "LOGISTICS_MANAGER" } }) }));

const RECORDS = {
  orders: { id: "o1", customerId: "outside-customer-page", status: "DRAFT", priority: "NORMAL", expectedDeliveryAt: null, createdAt: "2026-10-01T00:00:00Z", itemCount: 1 },
  products: { id: "p1", code: "SEM-CORRESPONDENCIA", name: "Produto devolvido", description: null, widthCm: 10, heightCm: 10, lengthCm: 10, weightKg: 1, fragile: false, stackable: true, rotationAllowed: true, active: true },
  trucks: { id: "t1", plate: "ABC1D23", model: "Caminhão devolvido", internalWidthCm: 240, internalHeightCm: 260, internalLengthCm: 600, maxWeightKg: 8000, active: true },
  customers: { id: "c1", name: "Cliente devolvido", city: "Campinas", state: "SP", active: true },
  drivers: { id: "d1", name: "Motorista devolvido", licenseCategory: "D", active: true },
};
const CASES = [
  { resource: "orders", Component: OrderListPage, label: "Buscar pedidos", visible: "Cliente não disponível", empty: "Nenhum pedido encontrado com esses filtros." },
  { resource: "products", Component: ProductListPage, label: "Buscar por código ou nome", visible: "SEM-CORRESPONDENCIA", empty: "Nenhum produto encontrado com esses filtros." },
  { resource: "trucks", Component: TruckListPage, label: "Buscar por placa ou modelo", visible: "ABC1D23", empty: "Nenhum caminhão encontrado com esses filtros." },
  { resource: "customers", Component: CustomerPanel, label: "Buscar cliente por nome ou cidade", visible: "Cliente devolvido", empty: "Nenhum cliente encontrado com essa busca." },
  { resource: "drivers", Component: DriverPanel, label: "Buscar motorista por nome", visible: "Motorista devolvido", empty: "Nenhum motorista encontrado com esses filtros." },
] as const;

beforeEach(() => {
  for (const resource of Object.keys(mocks) as (keyof typeof mocks)[]) {
    mocks[resource].mockReset().mockImplementation((params) => Promise.resolve(makePage([RECORDS[resource]], params.page, 2)));
  }
});

describe.each(CASES)("OC95 $resource", ({ resource, Component, label, visible, empty }) => {
  it("envia busca na página 1, preserva nas próximas páginas e exibe a resposta sem filtrar localmente", async () => {
    render(<MemoryRouter><Component /></MemoryRouter>);
    await screen.findByText(visible);
    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(mocks[resource]).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
    await screen.findByText("Página 2 de 2");
    fireEvent.change(screen.getByLabelText(label), { target: { value: "termo ausente no item" } });
    await waitFor(() => expect(mocks[resource]).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, search: "termo ausente no item" })));
    await screen.findByText("Página 1 de 2");
    expect(screen.getByText(visible)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(mocks[resource]).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, search: "termo ausente no item" })));
    if (resource === "orders") expect(mocks.customers).toHaveBeenCalledOnce();
  });

  it("mostra vazio filtrado quando o servidor devolve zero resultados", async () => {
    render(<MemoryRouter><Component /></MemoryRouter>);
    await screen.findByText(visible);
    mocks[resource].mockResolvedValue(makePage([]));
    fireEvent.change(screen.getByLabelText(label), { target: { value: "não encontrado" } });
    expect(await screen.findByText(empty)).toBeInTheDocument();
    expect(screen.queryByText(visible)).not.toBeInTheDocument();
  });

  it("preserva o tratamento de erro após mudar a busca", async () => {
    render(<MemoryRouter><Component /></MemoryRouter>);
    await screen.findByText(visible);
    mocks[resource].mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado."));
    fireEvent.change(screen.getByLabelText(label), { target: { value: "falha" } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Seu perfil não tem permissão");
  });
});

it.each(CASES.filter((item) => item.resource !== "orders"))("combina search e archive_status em $resource, reiniciando a página", async ({ resource, Component, label, visible }) => {
  render(<MemoryRouter><Component /></MemoryRouter>);
  await screen.findByText(visible);
  fireEvent.change(screen.getByLabelText(label), { target: { value: "alvo" } });
  await screen.findByText("Página 1 de 2");
  fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
  await screen.findByText("Página 2 de 2");
  fireEvent.change(screen.getByLabelText("Filtrar cadastros por arquivamento"), { target: { value: "archived" } });
  await waitFor(() => expect(mocks[resource]).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, search: "alvo", archiveStatus: "archived" })));
  await screen.findByText("Página 1 de 2");
  fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
  await waitFor(() => expect(mocks[resource]).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, search: "alvo", archiveStatus: "archived" })));
});

it.each([
  { Component: OrderListPage, resource: "orders", searchLabel: CASES[0].label, filterLabel: "Situação", value: "READY", key: "status", visible: CASES[0].visible },
  { Component: ProductListPage, resource: "products", searchLabel: CASES[1].label, filterLabel: "Filtrar por restrição", value: "restricted", key: "restriction", visible: CASES[1].visible },
] as const)("$resource preserva busca ao alterar $key e não reaplica o filtro aos items", async ({ Component, resource, searchLabel, filterLabel, value, key, visible }) => {
  render(<MemoryRouter><Component /></MemoryRouter>);
  await screen.findByText(visible);
  fireEvent.change(screen.getByLabelText(searchLabel), { target: { value: "alvo" } });
  await screen.findByText("Página 1 de 2");
  fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
  await screen.findByText("Página 2 de 2");
  fireEvent.change(screen.getByLabelText(filterLabel), { target: { value } });
  await waitFor(() => expect(mocks[resource]).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, search: "alvo", [key]: value })));
  await screen.findByText("Página 1 de 2");
  expect(screen.getByText(visible)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
  await waitFor(() => expect(mocks[resource]).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, search: "alvo", [key]: value })));
});
