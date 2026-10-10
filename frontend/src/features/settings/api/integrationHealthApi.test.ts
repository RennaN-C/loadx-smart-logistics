import { expect,it,vi } from "vitest";
import { api } from "../../../services/api";
import { getIntegrationHealth } from "./integrationHealthApi";
vi.mock("../../../services/api",()=>({api:{get:vi.fn()}}));
it("consulta endpoint ADMIN com limite de espera",async()=>{
  vi.mocked(api.get).mockResolvedValue({data:{components:[]}});
  expect(await getIntegrationHealth()).toEqual({components:[]});
  expect(api.get).toHaveBeenCalledWith("/integration-health",{timeout:8000});
});
