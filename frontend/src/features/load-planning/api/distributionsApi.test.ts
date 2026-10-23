import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { ApiError } from "../../../types/api";
import { distributionDto } from "../testing/distributionFixtures";
import { distributionAction, getDistribution, mapDistribution, optimizeDistribution, recoverOptimization, preflightDistribution, reprocessDistributionPart, type DistributionNeedDto } from "./distributionsApi";
vi.mock("../../../services/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());
describe("contrato de distribuição", () => {
  it.each([1, 2, 3])("preserva identidade e métricas de %i caminhões", (count) => {
    const result = mapDistribution(distributionDto(count));
    expect(result.truckCount).toBe(count);
    expect(result.volumes.map((v) => `${v.orderItemId}:${v.volumeIndex}`)).toEqual(Array.from({ length: count }, (_, i) => `order-item-1:${i + 1}`));
    result.parts.forEach((part, index) => {
      expect(part.loadPlan.items[0].volumeIndex).toBe(index + 1);
      expect(part.loadPlan.totalWeightKg).toBe((index + 1) * 12.5);
      expect(part.truck.id).toBe(part.loadPlan.truckId);
    });
  });
  it("otimiza com apenas order_ids e consulta sem escrita", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: distributionDto() });
    vi.mocked(api.get).mockResolvedValue({ data: distributionDto() });
    await optimizeDistribution(["order-1"]);
    expect(api.post).toHaveBeenCalledWith("/load-distributions/optimize", { order_ids: ["order-1"] }, undefined);
    await getDistribution("distribution-1");
    expect(api.get).toHaveBeenCalledWith("/load-distributions/distribution-1");
    expect(api.post).toHaveBeenCalledTimes(1);
  });
  it("envia chave idempotente e recupera por GET sem nova escrita", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: distributionDto() });
    vi.mocked(api.get).mockResolvedValue({ data: distributionDto() });
    await optimizeDistribution(["order-1"], "request-key");
    expect(api.post).toHaveBeenCalledWith("/load-distributions/optimize", { order_ids: ["order-1"] }, { headers: { "Idempotency-Key": "request-key" } });
    await recoverOptimization("request-key");
    expect(api.get).toHaveBeenCalledWith("/load-distributions/optimization-requests/request-key");
    expect(api.post).toHaveBeenCalledTimes(1);
  });
  it.each(["approve", "cancel"] as const)("envia %s no agregado ou parte", async (action) => {
    vi.mocked(api.post).mockResolvedValue({ data: distributionDto() });
    await distributionAction("d1", action);
    await distributionAction("d1", action, "p1");
    expect(api.post).toHaveBeenNthCalledWith(1, `/load-distributions/d1/${action}`, {});
    expect(api.post).toHaveBeenNthCalledWith(2, `/load-distributions/d1/parts/p1/${action}`, {});
  });
  it("reprocessa com versão esperada sem posições locais", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: distributionDto() });
    await reprocessDistributionPart("d1", "p1", "t2", "old-plan");
    expect(api.post).toHaveBeenCalledWith("/load-distributions/d1/parts/p1/reprocess", { truck_id: "t2", expected_load_plan_id: "old-plan" });
  });
  it("materializa preflight e motivos reais de inelegibilidade", async () => {
    const dto: DistributionNeedDto = { order_ids: ["order-1"], eligible_trucks: [distributionDto().parts[0].truck],
      ineligible_trucks: [{ truck_id: "t3", reason: "TRUCK_OPERATION_CONFLICT" }],
      volumes: [{ order_item_id: "oi1", volume_index: 3, order_id: "order-1", product_id: "p1",
        width_cm: 10, height_cm: 20, length_cm: 30, weight_kg: 5, delivery_sequence: 2,
        fragile: true, stackable: false, rotation_allowed: true }] };
    vi.mocked(api.post).mockResolvedValue({ data: dto });
    const result = await preflightDistribution(["order-1"]);
    expect(result.volumes[0]).toMatchObject({ volumeIndex: 3, widthCm: 10, weightKg: 5, rotationAllowed: true });
    expect(result.ineligibleTrucks[0].reason).toBe("TRUCK_OPERATION_CONFLICT");
  });
  it("preserva erro estruturado de capacidade sem retorno parcial", async () => {
    const failure = new ApiError("DISTRIBUTION_CAPACITY_INSUFFICIENT", "Sem capacidade", [{ volume_index: 3 }], 422);
    vi.mocked(api.post).mockRejectedValue(failure);
    await expect(optimizeDistribution(["order-1"])).rejects.toBe(failure);
  });
});
