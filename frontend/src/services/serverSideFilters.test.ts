import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import { listOrders } from "../features/orders/api/ordersApi";
import { listProducts } from "../features/products/api/productsApi";
import { listTrucks } from "../features/trucks/api/trucksApi";
import { listCustomers } from "../features/customers/api/customersApi";
import { listDrivers } from "../features/drivers/api/driversApi";

vi.mock("./api", () => ({ api: { get: vi.fn() } }));

const EMPTY = { items: [], page: 2, page_size: 3, total: 0, total_pages: 0 };

describe("APIs com whitelist OC95", () => {
  beforeEach(() => vi.mocked(api.get).mockReset().mockResolvedValue({ data: EMPTY }));

  it.each([
    ["trucks", listTrucks], ["customers", listCustomers], ["drivers", listDrivers],
  ] as const)("envia search + archive_status + paginação de %s", async (resource, load) => {
    await load({ search: "  São %_\\  ", archiveStatus: "archived", page: 2, pageSize: 3, sortOrder: "asc" });
    expect(api.get).toHaveBeenCalledWith(`/${resource}`, { params: { search: "São %_\\", archive_status: "archived", page: 2, page_size: 3, sort_order: "asc" } });
  });

  it("envia search/status de pedidos sem filtros de outros recursos", async () => {
    await listOrders({ search: " referência ", status: "READY", page: 2, pageSize: 3 });
    expect(api.get).toHaveBeenCalledWith("/orders", { params: { search: "referência", status: "READY", page: 2, page_size: 3, sort_order: "desc" } });
  });

  it.each(["restricted", "free"] as const)("combina restriction=%s com search e arquivamento", async (restriction) => {
    await listProducts({ search: "Caixa", restriction, archiveStatus: "all", page: 2, pageSize: 3 });
    expect(api.get).toHaveBeenCalledWith("/products", { params: { search: "Caixa", restriction, archive_status: "all", page: 2, page_size: 3, sort_order: "desc" } });
  });

  it.each([listOrders, listProducts, listTrucks, listCustomers, listDrivers])("omite busca whitespace e filtros opcionais ausentes", async (load) => {
    await load({ search: "   " });
    expect(api.get).toHaveBeenLastCalledWith(expect.any(String), { params: { page: 1, page_size: 20, sort_order: "desc" } });
  });
});
