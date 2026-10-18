import { describe, expect, it } from "vitest";

import { canReadReports } from "./permissions";
import type { AuthenticatedUser } from "../auth/types";

describe("canReadReports", () => {
  it("libera quem o backend libera", () => {
    expect(canReadReports("ADMIN")).toBe(true);
    expect(canReadReports("LOGISTICS_MANAGER")).toBe(true);
  });

  it("barra quem o backend barra", () => {
    // reports/router.py exige ADMIN ou LOGISTICS_MANAGER
    expect(canReadReports("CHECKER")).toBe(false);
    expect(canReadReports("DRIVER")).toBe(false);
  });

  it("barra sessão sem perfil resolvido", () => {
    expect(canReadReports(undefined)).toBe(false);
  });

  it("exige relatórios e pedidos separadamente para perfis personalizados", () => {
    const custom: AuthenticatedUser = {
      id: "u1", name: "Operador", email: "operador@example.test",
      role: "CUSTOM", active: true, createdAt: "2026-10-16T00:00:00Z",
      permissions: ["loadx.orders.read"],
    };
    expect(canReadReports(custom)).toBe(false);
    expect(canReadReports({ ...custom, permissions: ["loadx.reports.read"] })).toBe(false);
    expect(canReadReports({ ...custom, permissions: ["loadx.orders.read", "loadx.reports.read"] })).toBe(true);
    expect(canReadReports({ ...custom, active: false })).toBe(false);
  });
});
