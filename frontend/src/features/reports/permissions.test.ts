import { describe, expect, it } from "vitest";

import { canReadReports } from "./permissions";

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
});
