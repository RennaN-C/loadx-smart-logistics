import { describe, expect, it } from "vitest";
import { canCheckLoading, canManageLogistics, canOperateTrip } from "./permissions";

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
