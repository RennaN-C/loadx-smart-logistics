import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import { closeMaintenance, createMaintenance, listMaintenances } from "./maintenanceApi";
vi.mock("../../../services/api",()=>({api:{get:vi.fn(),post:vi.fn()}}));
const dto={id:"m1",truck_id:"t1",kind:"PREVENTIVE",starts_at:"2026-01-01T00:00:00Z",ends_at:null,description:"Revisão",workshop:null,notes:null,cost:null,odometer_km:1000,completion_odometer_km:null,next_service_at:null,next_service_km:null,closed_at:null,created_at:"2026-01-01T00:00:00Z"};
beforeEach(()=>vi.clearAllMocks());
describe("contrato de manutenção",()=>{
 it("mapeia histórico paginado e valores opcionais",async()=>{
  vi.mocked(api.get).mockResolvedValue({data:{items:[dto],page:1,page_size:20,total:1,total_pages:1}});
  const result=await listMaintenances("t1");expect(result.items[0]).toMatchObject({truckId:"t1",odometerKm:1000,endsAt:null,cost:null});expect(api.get).toHaveBeenCalledWith("/trucks/t1/maintenances",expect.any(Object));
 });
 it("envia criação em snake_case com datas explícitas",async()=>{
  vi.mocked(api.post).mockResolvedValue({data:dto});await createMaintenance("t1",{kind:"CORRECTIVE",startsAt:"2026-01-01T00:00:00Z",description:"Conserto",odometerKm:1000});
  expect(api.post).toHaveBeenCalledWith("/trucks/t1/maintenances",expect.objectContaining({kind:"CORRECTIVE",starts_at:"2026-01-01T00:00:00Z",odometer_km:1000}));
 });
 it("preserva omissão ou null explícito na próxima revisão",async()=>{
  vi.mocked(api.post).mockResolvedValue({data:dto});await closeMaintenance("t1","m1",{});expect(vi.mocked(api.post).mock.calls[0][1]).not.toHaveProperty("next_service_km");
  await closeMaintenance("t1","m1",{nextServiceKm:null,nextServiceAt:null});expect(api.post).toHaveBeenLastCalledWith("/trucks/t1/maintenances/m1/close",{odometer_km:undefined,next_service_km:null,next_service_at:null});
 });
});
