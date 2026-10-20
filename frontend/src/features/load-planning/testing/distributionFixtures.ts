import { mapDistribution, type DistributionDto } from "../api/distributionsApi";
import type { DistributionStatus } from "../types";

export function distributionDto(count = 2, status: DistributionStatus = "PROPOSED"): DistributionDto {
  const approved = status === "APPROVED";
  return { id: "distribution-1", status, created_by: "user-1", created_at: "2026-10-20T12:00:00Z",
    order_ids: ["order-1"], truck_count: count, volume_count: count,
    parts: Array.from({ length: count }, (_, index) => {
      const i = index + 1;
      return { id: `part-${i}`, status: approved ? "APPROVED" : "PENDING",
        truck: { id: `truck-${i}`, plate: `TST${i}A23`, model: `Baú fictício ${i}`,
          width_cm: 240, height_cm: 260, length_cm: 600, max_weight_kg: 5000 },
        load_plan: { id: `plan-${i}`, distribution_id: "distribution-1", truck_id: `truck-${i}`,
          recalculated_from_id: null, status: approved ? "APPROVED" : "CALCULATED",
          internal_volume_cm3: 37440000, used_volume_cm3: 144000,
          occupancy_percent: i * 10, total_weight_kg: i * 12.5, loaded_count: 1, unloaded_count: 0,
          algorithm_version: "heuristic-v1", created_at: "2026-10-20T12:00:00Z",
          approved_at: approved ? "2026-10-20T12:05:00Z" : null, order_ids: ["order-1"],
          items: [{ id: `item-${i}`, order_id: "order-1", order_item_id: "order-item-1", product_id: "product-1",
            volume_index: i, quantity: count, delivery_sequence: 1, product_code: "CX-100", product_name: "Caixa fictícia",
            original_width_cm: 40, original_height_cm: 30, original_length_cm: 60, weight_kg: i * 12.5,
            fragile: false, stackable: true, rotation_allowed: true, x_cm: 0, y_cm: 0, z_cm: 0,
            width_cm: 40, height_cm: 30, length_cm: 60, rotation_code: "XYZ", loading_sequence: 1,
            placed: true, rejection_reason: null }] } };
    }),
    volumes: Array.from({ length: count }, (_, index) => ({ order_item_id: "order-item-1", volume_index: index + 1,
      order_id: "order-1", product_id: "product-1", quantity: count, part_id: `part-${index + 1}` })) };
}
export function makeDistribution(count = 2, status: DistributionStatus = "PROPOSED") {
  return mapDistribution(distributionDto(count, status));
}
