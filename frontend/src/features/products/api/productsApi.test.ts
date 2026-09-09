import { describe, expect, it } from "vitest";

import { mapProductFromDto, mapProductPageFromDto } from "./productsApi";

const DTO = {
  id: "33333333-3333-3333-3333-333333333333",
  code: "CX-100",
  name: "Caixa média",
  description: "Papelão reforçado",
  width_cm: 40,
  height_cm: 30,
  length_cm: 60,
  weight_kg: 12.5,
  fragile: false,
  stackable: true,
  rotation_allowed: true,
  created_at: "2026-08-01T12:00:00Z",
};

describe("mapProductFromDto", () => {
  it("converte snake_case do backend para camelCase", () => {
    expect(mapProductFromDto(DTO)).toEqual({
      id: "33333333-3333-3333-3333-333333333333",
      code: "CX-100",
      name: "Caixa média",
      description: "Papelão reforçado",
      widthCm: 40,
      heightCm: 30,
      lengthCm: 60,
      weightKg: 12.5,
      fragile: false,
      stackable: true,
      rotationAllowed: true,
      createdAt: "2026-08-01T12:00:00Z",
    });
  });

  it("preserva weight_kg como número, sem coerção (D06/ADR-016)", () => {
    const result = mapProductFromDto({ ...DTO, weight_kg: 12.5 });

    expect(result.weightKg).toBe(12.5);
    expect(typeof result.weightKg).toBe("number");
  });

  it("preserva description nula", () => {
    expect(mapProductFromDto({ ...DTO, description: null }).description).toBeNull();
  });
});

describe("mapProductPageFromDto", () => {
  it("converte o envelope paginado para camelCase", () => {
    expect(
      mapProductPageFromDto({ items: [DTO], page: 2, page_size: 20, total: 21, total_pages: 2 }),
    ).toEqual({
      items: [mapProductFromDto(DTO)],
      page: 2,
      pageSize: 20,
      total: 21,
      totalPages: 2,
    });
  });
});
