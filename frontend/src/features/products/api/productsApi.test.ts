import { describe, expect, it } from "vitest";

import { mapProductFromDto } from "./productsApi";

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

  it("aceita weight_kg como string, já que o campo é Decimal no backend", () => {
    expect(mapProductFromDto({ ...DTO, weight_kg: "12.500" }).weightKg).toBe(12.5);
  });

  it("preserva description nula", () => {
    expect(mapProductFromDto({ ...DTO, description: null }).description).toBeNull();
  });
});
