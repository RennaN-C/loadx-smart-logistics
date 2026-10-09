import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { closeMaintenance, createMaintenance, listMaintenances } from "../api/maintenanceApi";
import { getTruck, updateTruck } from "../api/trucksApi";
import type { Truck, TruckMaintenance } from "../types";
import { MaintenancePanel } from "./MaintenancePanel";
vi.mock("../../auth/hooks/useAuth");
vi.mock("../api/maintenanceApi");
vi.mock("../api/trucksApi");
const truck: Truck = { id:"t1",plate:"ABC1D23",model:"Baú",internalWidthCm:100,internalHeightCm:100,internalLengthCm:100,maxWeightKg:1000,active:true,createdAt:"2026-01-01T00:00:00Z",odometerKm:1000,nextServiceKm:2000,nextServiceAt:"2099-01-01T00:00:00Z" };
const record: TruckMaintenance = { id:"m1",truckId:"t1",kind:"PREVENTIVE",startsAt:"2020-01-01T00:00:00Z",endsAt:null,description:"Revisão dos freios",workshop:"Oficina fictícia",notes:null,cost:100,odometerKm:1000,completionOdometerKm:null,nextServiceAt:null,nextServiceKm:null,closedAt:null,createdAt:"2020-01-01T00:00:00Z" };
const onChanged=vi.fn().mockResolvedValue(undefined);
function show() { render(<MaintenancePanel truck={truck} onChanged={onChanged}/>); }
beforeEach(()=>{
 vi.clearAllMocks();
 vi.mocked(useAuth).mockReturnValue({user:{id:"u1",name:"Gestor",email:"manager@example.test",role:"LOGISTICS_MANAGER",active:true,createdAt:"2026-01-01T00:00:00Z"},status:"authenticated",login:vi.fn(),logout:vi.fn()});
 vi.mocked(listMaintenances).mockResolvedValue({items:[record],page:1,pageSize:20,total:1,totalPages:1});
 vi.mocked(getTruck).mockResolvedValue(truck);vi.mocked(updateTruck).mockResolvedValue(truck);
 vi.mocked(createMaintenance).mockResolvedValue(record);vi.mocked(closeMaintenance).mockResolvedValue({...record,closedAt:"2026-01-01T00:00:00Z"});
});
describe("manutenção da frota",()=>{
 it("exibe histórico e programação da revisão",async()=>{
  show();await screen.findByText("Revisão dos freios");
  expect(screen.getByText(/Quilometragem atual: 1000/)).toBeInTheDocument();expect(screen.getByText(/2000 km/)).toBeInTheDocument();expect(screen.getByText("Em manutenção")).toBeInTheDocument();
 });
 it("registra manutenção corretiva com custo opcional",async()=>{
  show();await screen.findByText("Revisão dos freios");fireEvent.click(screen.getByRole("button",{name:"Nova manutenção"}));
  fireEvent.change(screen.getByLabelText("TIPO"),{target:{value:"CORRECTIVE"}});fireEvent.change(screen.getByLabelText("DESCRIÇÃO"),{target:{value:"Troca fictícia"}});fireEvent.click(screen.getByRole("button",{name:"Registrar manutenção"}));
  await waitFor(()=>expect(createMaintenance).toHaveBeenCalledWith("t1",expect.objectContaining({kind:"CORRECTIVE",description:"Troca fictícia",cost:null,odometerKm:1000})));
  await waitFor(()=>expect(onChanged).toHaveBeenCalled());
 });
 it("encerra com revisão por km preservando campos omitidos",async()=>{
  show();fireEvent.click(await screen.findByRole("button",{name:"Encerrar manutenção"}));fireEvent.change(screen.getByLabelText("PRÓXIMA REVISÃO (KM)"),{target:{value:"5000"}});fireEvent.click(screen.getByRole("button",{name:"Confirmar encerramento"}));
  await waitFor(()=>expect(closeMaintenance).toHaveBeenCalledWith("t1","m1",{odometerKm:1000,nextServiceKm:5000}));
 });
 it("atualiza quilometragem e apresenta erro do backend",async()=>{
  vi.mocked(updateTruck).mockRejectedValue(new ApiError("ODOMETER_DECREASE","A quilometragem não pode diminuir."));show();await screen.findByText("Revisão dos freios");fireEvent.change(screen.getByLabelText("Atualizar quilometragem"),{target:{value:"1500"}});fireEvent.click(screen.getByRole("button",{name:"Salvar quilometragem"}));
  expect(await screen.findByText("A quilometragem não pode diminuir.")).toBeInTheDocument();expect(updateTruck).toHaveBeenCalledWith("t1",{odometerKm:1500});expect(onChanged).not.toHaveBeenCalled();
 });
 it("conferente consulta histórico sem ações administrativas",async()=>{
  const auth=vi.mocked(useAuth).getMockImplementation()!();vi.mocked(useAuth).mockReturnValue({...auth,user:{...auth.user!,role:"CHECKER"}});show();await screen.findByText("Revisão dos freios");expect(screen.queryByRole("button",{name:"Nova manutenção"})).not.toBeInTheDocument();expect(screen.queryByRole("button",{name:"Encerrar manutenção"})).not.toBeInTheDocument();
 });
 it("exibe vazio e falha de consulta",async()=>{
  vi.mocked(listMaintenances).mockRejectedValue(new ApiError("ERROR","Não foi possível consultar."));show();expect(await screen.findByText("Não foi possível consultar.")).toBeInTheDocument();
 });
 it("distingue manutenção futura e histórico encerrado",async()=>{
  vi.mocked(listMaintenances).mockResolvedValue({items:[{...record,startsAt:"2099-01-01T00:00:00Z"},{...record,id:"m2",closedAt:"2026-01-01T00:00:00Z"}],page:1,pageSize:20,total:2,totalPages:1});show();expect(await screen.findByText("Programada")).toBeInTheDocument();expect(screen.getByText("Encerrada")).toBeInTheDocument();
 });
});
