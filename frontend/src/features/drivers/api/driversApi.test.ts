import { describe, expect, it } from "vitest";

import { mapDriverFromDto } from "./driversApi";

describe("mapDriverFromDto", () => {
  it("converte snake_case do backend para camelCase", () => {
    expect(
      mapDriverFromDto({
        id: "d1",
        name: "Carlos Pereira",
        document: "123.456.789-00",
        phone: "(11) 91111-1111",
        license_number: "01234567890",
        license_category: "E",
        active: true,
        created_at: "2026-08-01T12:00:00Z",
      }),
    ).toEqual({
      id: "d1",
      name: "Carlos Pereira",
      document: "123.456.789-00",
      phone: "(11) 91111-1111",
      licenseNumber: "01234567890",
      licenseCategory: "E",
      active: true,
      createdAt: "2026-08-01T12:00:00Z",
    });
  });

  it("preserva categoria nula", () => {
    const result = mapDriverFromDto({
      id: "d1",
      name: "Rita Alves",
      document: "987.654.321-00",
      phone: "(11) 92222-2222",
      license_number: "09876543210",
      license_category: null,
      active: true,
      created_at: "2026-08-01T12:00:00Z",
    });

    expect(result.licenseCategory).toBeNull();
  });
});
