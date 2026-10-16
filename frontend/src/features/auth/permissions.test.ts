import { describe, expect, it } from "vitest";
import { hasPermission, canCheckLoading, canManageLogistics, canOperateTrip } from "./permissions";
import type { AuthenticatedUser } from "./types";
const user: AuthenticatedUser = { id: "u1", name: "Exemplo", email: "exemplo@example.test", active: true, role: "CUSTOM", createdAt: "2026-10-16T00:00:00Z", permissions: ["loadx.trucks.read"] };
describe("permissões efetivas OC112", () => {
  it("usa a projeção exata sem herdar acesso do gerente", () => { expect(hasPermission(user, "loadx.trucks.read")).toBe(true); expect(hasPermission(user, "loadx.trucks.manage")).toBe(false); expect(hasPermission(user, "loadx.users.manage")).toBe(false); });
  it("nega perfil personalizado sem permissões ou usuário inativo", () => { expect(hasPermission({ ...user, permissions: undefined }, "loadx.trucks.read")).toBe(false); expect(hasPermission({ ...user, active: false }, "loadx.trucks.read")).toBe(false); });
  it("não acrescenta poderes por nome do papel quando há projeção", () => { expect(hasPermission({ ...user, role: "ADMIN", permissions: [] }, "loadx.users.manage")).toBe(false); });
  it.each(["ADMIN", "LOGISTICS_MANAGER"] as const)("preserva gestão logística de %s", (role) => { expect(hasPermission(role, "loadx.trucks.manage")).toBe(true); expect(hasPermission(role, "loadx.planning.approve")).toBe(true); });
  it("preserva vínculos e separa identidade de conferência", () => { expect(hasPermission("DRIVER", "loadx.trips.own")).toBe(true); expect(hasPermission("DRIVER", "loadx.trips.manage")).toBe(false); expect(hasPermission("CHECKER", "loadx.loading.operate")).toBe(true); expect(hasPermission("LOGISTICS_MANAGER", "loadx.loading.operate")).toBe(false); });
});

describe("hierarquia operacional v1.2.0", () => {
  it("permite ao ADMIN todas as funções gerenciais do módulo", () => {
    expect(canManageLogistics("ADMIN")).toBe(true);
    expect(canCheckLoading("ADMIN")).toBe(true);
    expect(canOperateTrip("ADMIN")).toBe(true);
  });

  it("limita o gerente às operações logísticas, sem poderes de conferente", () => {
    expect(canManageLogistics("LOGISTICS_MANAGER")).toBe(true);
    expect(canCheckLoading("LOGISTICS_MANAGER")).toBe(false);
    expect(canOperateTrip("LOGISTICS_MANAGER")).toBe(true);
  });

  it("preserva os privilégios específicos do conferente e do motorista", () => {
    expect(canManageLogistics("CHECKER")).toBe(false);
    expect(canCheckLoading("CHECKER")).toBe(true);
    expect(canOperateTrip("CHECKER")).toBe(false);
    expect(canManageLogistics("DRIVER")).toBe(false);
    expect(canCheckLoading("DRIVER")).toBe(false);
    expect(canOperateTrip("DRIVER")).toBe(true);
    expect(canManageLogistics(undefined)).toBe(false);
  });
});
