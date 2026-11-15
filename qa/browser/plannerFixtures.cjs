/* Synthetic, fixed browser fixtures. Never imported by the application bundle. */
const date = "2026-11-15T12:00:00Z";
const id = (value) => `00000000-0000-4000-8000-${String(value).padStart(12, "0")}`;

function createPlannerFixtures({ empty = false, singleTruck = false } = {}) {
  const partCount = singleTruck ? 1 : 2;
  const countPerPart = empty ? 0 : 200 / partCount;
  const parts = Array.from({ length: partCount }, (_, partIndex) => {
    const offset = partIndex * 1000;
    const truck = {
      id: id(20 + partIndex), plate: partIndex === 0 ? "TST1A23" : "TST2B45",
      model: partIndex === 0 ? "Baú longo fictício" : "Baú compacto fictício",
      width_cm: partIndex === 0 ? 240 : 220,
      height_cm: partIndex === 0 ? 260 : 240,
      length_cm: partIndex === 0 ? 600 : 480,
      max_weight_kg: partIndex === 0 ? 8000 : 5000,
    };
    const columns = 5;
    const rows = singleTruck ? 10 : 5;
    const items = Array.from({ length: countPerPart }, (_, index) => ({
      id: id(100 + offset + index), order_id: id(4), order_item_id: id(5 + partIndex),
      product_id: id(6 + partIndex), volume_index: index + 1, quantity: countPerPart,
      delivery_sequence: 1 + Math.floor(index / 25),
      product_code: `CX-${partIndex + 1}-${String(index + 1).padStart(3, "0")}`,
      product_name: `Caixa de demonstração ${index + 1}`,
      original_width_cm: 40, original_height_cm: 30, original_length_cm: 60,
      weight_kg: 10, fragile: index % 13 === 0, stackable: true, rotation_allowed: true,
      x_cm: (index % columns) * 40,
      y_cm: Math.floor(index / (columns * rows)) * 30,
      z_cm: Math.floor((index % (columns * rows)) / columns) * 60,
      width_cm: 40, height_cm: 30, length_cm: 60,
      rotation_code: "XYZ", loading_sequence: index + 1,
    }));
    const internalVolume = truck.width_cm * truck.height_cm * truck.length_cm;
    const usedVolume = countPerPart * 40 * 30 * 60;
    const plan = {
      id: id(30 + partIndex), truck_id: truck.id, distribution_id: id(10),
      recalculated_from_id: null, status: "APPROVED", orders_ready_for_approval: false,
      internal_volume_cm3: internalVolume, used_volume_cm3: usedVolume,
      occupancy_percent: (usedVolume / internalVolume) * 100,
      total_weight_kg: countPerPart * 10, loaded_count: countPerPart, unloaded_count: 0,
      algorithm_version: "heuristic-v1", created_at: date, approved_at: date,
      order_ids: [id(4)], items: items.map((item) => ({ ...item, placed: true, rejection_reason: null })),
    };
    return { id: id(40 + partIndex), status: "APPROVED", truck, load_plan: plan, visualization: { truck, items, unloaded_items: [] } };
  });
  const distribution = {
    id: id(10), status: "APPROVED", created_by: id(1), created_at: date,
    order_ids: [id(4)], truck_count: parts.length, volume_count: empty ? 0 : 200,
    parts: parts.map(({ visualization: _visualization, ...part }) => part),
    volumes: parts.flatMap((part) => part.visualization.items.map((item) => ({
      order_item_id: item.order_item_id, volume_index: item.volume_index,
      order_id: item.order_id, product_id: item.product_id, quantity: item.quantity, part_id: part.id,
    }))),
  };
  return { id, date, distribution, parts };
}

module.exports = { createPlannerFixtures };
