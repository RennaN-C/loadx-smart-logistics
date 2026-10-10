import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { getIntegrationHealth, type IntegrationHealthReport } from "../api/integrationHealthApi";
import { IntegrationHealthPanel } from "./IntegrationHealthPanel";
vi.mock("../api/integrationHealthApi");
const REPORT: IntegrationHealthReport = {
  checked_at: "2026-10-10T12:00:00Z", correlation_id: "00000000-0000-0000-0000-000000000108", overall_status: "PARTIAL",
  components: [
    { component:"api",mode:"INTERNAL",status:"AVAILABLE",configured:true,reason_code:"LIVE" },
    { component:"database",mode:"INTERNAL",status:"AVAILABLE",configured:true,reason_code:"READY" },
    { component:"whatsapp",mode:"MOCK",status:"SIMULATED",configured:true,reason_code:"MOCK_PROVIDER" },
    { component:"ai",mode:"MOCK",status:"SIMULATED",configured:true,reason_code:"MOCK_PROVIDER" },
    { component:"webhook",mode:"INTERNAL",status:"NOT_IMPLEMENTED",configured:false,reason_code:"OC83_PENDING" },
    { component:"notifications",mode:"INTERNAL",status:"LIMITED",configured:true,reason_code:"OC84_PENDING" },
  ],
};
beforeEach(() => { vi.resetAllMocks(); vi.mocked(getIntegrationHealth).mockResolvedValue(REPORT); });
describe("OC108: painel de integrações", () => {
  it("carrega sinais honestos e não promete entrega real", async () => {
    render(<IntegrationHealthPanel />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando");
    await screen.findByRole("heading", { name:"WhatsApp" });
    expect(screen.getAllByText("SIMULADO")).toHaveLength(2);
    expect(screen.getByText(/Não há conexão, envio ou confirmação de entrega pela Meta/)).toBeInTheDocument();
    expect(screen.getByText("NÃO IMPLEMENTADO")).toBeInTheDocument();
    expect(screen.getByText("LIMITADO")).toBeInTheDocument();
    expect(screen.getByText(REPORT.correlation_id)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name:/enviar|testar conexão/i })).not.toBeInTheDocument();
  });
  it.each(["NOT_CONFIGURED","UNAVAILABLE","TIMEOUT","AVAILABLE"] as const)("representa IA real no estado %s sem ativação fictícia", async (status) => {
    vi.mocked(getIntegrationHealth).mockResolvedValue({ ...REPORT, components:[{ component:"ai",mode:"REAL",status,configured:status==="AVAILABLE",reason_code: status==="AVAILABLE" ? "READY" : "NOT_CONFIGURED" }] });
    render(<IntegrationHealthPanel />);
    await screen.findByRole("heading", { name:"Inteligência artificial" });
    expect(screen.getByText("Real (sujeito à configuração e aprovação)")).toBeInTheDocument();
    expect(screen.getByText({ NOT_CONFIGURED:"NÃO CONFIGURADO", UNAVAILABLE:"FALHA", TIMEOUT:"TEMPO ESGOTADO", AVAILABLE:"DISPONÍVEL" }[status])).toBeInTheDocument();
  });
  it("falha parcial preserva demais indicadores", async () => {
    vi.mocked(getIntegrationHealth).mockResolvedValue({ ...REPORT, overall_status:"DEGRADED",components:REPORT.components.map((item) => item.component==="database" ? {...item,status:"TIMEOUT",reason_code:"TIMEOUT"} : item) });
    render(<IntegrationHealthPanel />);
    await screen.findByText("TEMPO ESGOTADO");
    expect(screen.getAllByText("SIMULADO")).toHaveLength(2);
    expect(screen.getByText(/Saúde degradada/)).toBeInTheDocument();
  });
  it("erro de API não exibe detalhes privados e permite repetir", async () => {
    vi.mocked(getIntegrationHealth).mockRejectedValueOnce(new ApiError("NETWORK_ERROR","token-secreto stack trace privatehost"));
    render(<IntegrationHealthPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível consultar");
    expect(screen.queryByText(/token-secreto/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name:"Atualizar estados" }));
    await screen.findByRole("heading", { name:"WhatsApp" });
    expect(getIntegrationHealth).toHaveBeenCalledTimes(2);
  });
  it.each([401,403])("diferencia falha de autorização HTTP %s", async (status) => {
    vi.mocked(getIntegrationHealth).mockRejectedValue(new ApiError("AUTH_FAILED","segredo",[],status));
    render(<IntegrationHealthPanel />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(status===403 ? "exclusiva do ADMIN" : "Entre novamente");
  });
  it("atualização falha conserva último snapshot explicitamente desatualizado", async () => {
    render(<IntegrationHealthPanel />);
    await screen.findByRole("heading", { name:"WhatsApp" });
    vi.mocked(getIntegrationHealth).mockRejectedValue(new Error("timeout"));
    fireEvent.click(screen.getByRole("button", { name:"Atualizar estados" }));
    await screen.findByRole("alert");
    expect(screen.getByText(/podem estar desatualizados/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name:"WhatsApp" })).toBeInTheDocument();
  });
  it("perda de autorização limpa snapshot anterior", async () => {
    render(<IntegrationHealthPanel />);
    await screen.findByRole("heading", { name:"WhatsApp" });
    vi.mocked(getIntegrationHealth).mockRejectedValue(new ApiError("AUTH_FORBIDDEN","negado",[],403));
    fireEvent.click(screen.getByRole("button", { name:"Atualizar estados" }));
    await screen.findByRole("alert");
    expect(screen.queryByRole("heading", { name:"WhatsApp" })).not.toBeInTheDocument();
  });
  it("trata ausência de indicadores sem criar cards fictícios", async () => {
    vi.mocked(getIntegrationHealth).mockResolvedValue({ ...REPORT,components:[] });
    render(<IntegrationHealthPanel />);
    expect(await screen.findByText("Nenhum indicador foi disponibilizado nesta consulta.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name:"WhatsApp" })).not.toBeInTheDocument();
  });
  it("configuração desconhecida não é apresentada como ausente", async () => {
    vi.mocked(getIntegrationHealth).mockResolvedValue({ ...REPORT,components:[{ component:"ai",mode:"REAL",status:"UNAVAILABLE",configured:null,reason_code:"PROVIDER_FAILED" }] });
    render(<IntegrationHealthPanel />);
    await screen.findByText("Não verificada");
    expect(screen.queryByText("Ausente")).not.toBeInTheDocument();
  });
  it("consulta pendente bloqueia botão e não inicia polling", async () => {
    vi.mocked(getIntegrationHealth).mockReturnValue(new Promise(() => {}));
    render(<IntegrationHealthPanel />);
    expect(screen.getByRole("button", { name:"Consultando…" })).toBeDisabled();
    await waitFor(() => expect(getIntegrationHealth).toHaveBeenCalledOnce());
  });
});
