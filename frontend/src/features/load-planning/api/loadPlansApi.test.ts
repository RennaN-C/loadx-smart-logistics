import { describe, expect, it } from "vitest";

import { mapLoadPlanFromDto, mapVisualizationFromDto } from "./loadPlansApi";

const ITEM_DTO = {
  id: "li1",
  order_id: "o1",
  order_item_id: "oi1",
  product_id: "p1",
  volume_index: 1,
  quantity: 2,
  delivery_sequence: 1,
  product_code: "CX-100",
  product_name: "Caixa média",
  original_width_cm: 40,
  original_height_cm: 30,
  original_length_cm: 60,
  weight_kg: 12.5,
  fragile: false,
  stackable: true,
  rotation_allowed: true,
};

describe("mapLoadPlanFromDto", () => {
  it("converte o plano e os itens colocados", () => {
    const plan = mapLoadPlanFromDto({
      id: "lp1",
      truck_id: "t1",
      recalculated_from_id: null,
      status: "CALCULATED",
      internal_volume_cm3: 37_440_000,
      used_volume_cm3: 144_000,
      occupancy_percent: 0.38,
      total_weight_kg: 25,
      loaded_count: 1,
      unloaded_count: 0,
      algorithm_version: "v1",
      created_at: "2026-08-07T12:00:00Z",
      approved_at: null,
      order_ids: ["o1"],
      items: [
        {
          ...ITEM_DTO,
          x_cm: 0,
          y_cm: 0,
          z_cm: 0,
          width_cm: 40,
          height_cm: 30,
          length_cm: 60,
          rotation_code: "XYZ",
          loading_sequence: 1,
          placed: true,
          rejection_reason: null,
        },
      ],
    });

    expect(plan.occupancyPercent).toBe(0.38);
    expect(plan.items[0]).toMatchObject({
      productCode: "CX-100",
      originalWidthCm: 40,
      xCm: 0,
      widthCm: 40,
      rotationCode: "XYZ",
      loadingSequence: 1,
      placed: true,
      rejectionReason: null,
    });
  });

  it("preserva posição nula e motivo no item recusado", () => {
    const plan = mapLoadPlanFromDto({
      id: "lp1",
      truck_id: "t1",
      recalculated_from_id: "lp0",
      status: "CALCULATED",
      internal_volume_cm3: 1,
      used_volume_cm3: 0,
      occupancy_percent: 0,
      total_weight_kg: 0,
      loaded_count: 0,
      unloaded_count: 1,
      algorithm_version: "v1",
      created_at: "2026-08-07T12:00:00Z",
      approved_at: null,
      order_ids: ["o1"],
      items: [
        {
          ...ITEM_DTO,
          x_cm: null,
          y_cm: null,
          z_cm: null,
          width_cm: null,
          height_cm: null,
          length_cm: null,
          rotation_code: null,
          loading_sequence: null,
          placed: false,
          rejection_reason: "TRUCK_DIMENSIONS_EXCEEDED",
        },
      ],
    });

    expect(plan.recalculatedFromId).toBe("lp0");
    expect(plan.items[0].xCm).toBeNull();
    expect(plan.items[0].placed).toBe(false);
    expect(plan.items[0].rejectionReason).toBe("TRUCK_DIMENSIONS_EXCEEDED");
  });
});

describe("mapVisualizationFromDto", () => {
  it("separa caminhão, colocados e recusados", () => {
    const view = mapVisualizationFromDto({
      truck: {
        id: "t1",
        plate: "ABC1D23",
        model: "Baú médio",
        width_cm: 240,
        height_cm: 260,
        length_cm: 600,
        max_weight_kg: 8000,
      },
      items: [
        {
          ...ITEM_DTO,
          x_cm: 10,
          y_cm: 0,
          z_cm: 20,
          width_cm: 40,
          height_cm: 30,
          length_cm: 60,
          rotation_code: "XZY",
          loading_sequence: 3,
        },
      ],
      unloaded_items: [{ ...ITEM_DTO, id: "li2", rejection_reason: "COLLISION" }],
    });

    expect(view.truck).toEqual({
      id: "t1",
      plate: "ABC1D23",
      model: "Baú médio",
      widthCm: 240,
      heightCm: 260,
      lengthCm: 600,
      maxWeightKg: 8000,
    });
    expect(view.items[0]).toMatchObject({ xCm: 10, zCm: 20, rotationCode: "XZY", loadingSequence: 3 });
    expect(view.unloadedItems[0].rejectionReason).toBe("COLLISION");
  });
});
