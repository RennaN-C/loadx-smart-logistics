import { describe, expect, it } from "vitest";

import { mapTruckFromDto } from "./trucksApi";

const DTO = {
  id: "22222222-2222-2222-2222-222222222222",
  plate: "ABC1D23",
  model: "Baú médio",
  internal_width_cm: 240,
  internal_height_cm: 260,
  internal_length_cm: 600,
  max_weight_kg: 8000,
  active: true,
  created_at: "2026-08-01T12:00:00Z",
};

describe("mapTruckFromDto", () => {
  it("converte snake_case do backend para camelCase", () => {
    expect(mapTruckFromDto(DTO)).toEqual({
      id: "22222222-2222-2222-2222-222222222222",
      plate: "ABC1D23",
      model: "Baú médio",
      internalWidthCm: 240,
      internalHeightCm: 260,
      internalLengthCm: 600,
      maxWeightKg: 8000,
      active: true,
      createdAt: "2026-08-01T12:00:00Z",
    });
  });

  it("aceita max_weight_kg como string, já que o campo é Decimal no backend", () => {
    const result = mapTruckFromDto({ ...DTO, max_weight_kg: "8000.50" });

    expect(result.maxWeightKg).toBe(8000.5);
  });
});
