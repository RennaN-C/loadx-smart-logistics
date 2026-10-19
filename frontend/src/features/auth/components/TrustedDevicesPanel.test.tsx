import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api/trustedDevicesApi";
import { TrustedDevicesPanel } from "./TrustedDevicesPanel";
vi.mock("../api/trustedDevicesApi");
const device = { id: "abcdefgh-device", created_at: "2026-10-19T12:00:00Z", last_used_at: "2026-10-19T12:01:00Z", expires_at: "2026-11-18T12:00:00Z", current: true };
const data = { enabled: true, lifetime_days: 30, items: [device] };
beforeEach(() => { vi.resetAllMocks(); vi.mocked(api.listTrustedDevices).mockResolvedValue(data); });
describe("dispositivos confiáveis próprios", () => {
  it("apresenta carregamento, dados reais e limites da confiança", async () => {
    render(<TrustedDevicesPanel />);
    expect(screen.getByText("Consultando dispositivos confiáveis…")).toBeInTheDocument();
    await screen.findByText("Este navegador");
    expect(screen.getByText(/A senha e os prazos normais/)).toBeInTheDocument();
    expect(screen.getByText("Último uso")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remover este navegador" })).toBeEnabled();
  });
  it("esquece o dispositivo, reconsulta e informa manutenção da sessão", async () => {
    render(<TrustedDevicesPanel />);
    const button = await screen.findByRole("button", { name: "Remover este navegador" });
    vi.mocked(api.listTrustedDevices).mockResolvedValue({ ...data, items: [] });
    fireEvent.click(button);
    await screen.findByText("Nenhum dispositivo confiável ativo.");
    expect(api.forgetCurrentDevice).toHaveBeenCalledOnce();
    expect(screen.getByText(/A sessão atual permanece ativa/)).toBeInTheDocument();
  });
  it("remove outro dispositivo pelo UUID sem esquecer o atual", async () => {
    vi.mocked(api.listTrustedDevices).mockResolvedValue({ ...data, items: [{ ...device, current: false }] });
    render(<TrustedDevicesPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Remover dispositivo abcdefgh" }));
    await waitFor(() => expect(api.revokeTrustedDevice).toHaveBeenCalledWith(device.id));
    expect(api.forgetCurrentDevice).not.toHaveBeenCalled();
  });
  it("exige confirmação antes de revogar todos e permite cancelar", async () => {
    render(<TrustedDevicesPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Revogar todos os dispositivos" }));
    expect(api.revokeAllTrustedDevices).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    fireEvent.click(screen.getByRole("button", { name: "Revogar todos os dispositivos" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar revogação de todos" }));
    await waitFor(() => expect(api.revokeAllTrustedDevices).toHaveBeenCalledOnce());
  });
  it("trata falha de consulta e nova tentativa", async () => {
    vi.mocked(api.listTrustedDevices).mockRejectedValueOnce(new Error());
    render(<TrustedDevicesPanel />);
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Consultar novamente" }));
    await screen.findByText("Este navegador");
  });
  it("mantém registro após falha ao revogar e bloqueia envio duplicado", async () => {
    vi.mocked(api.forgetCurrentDevice).mockRejectedValueOnce(new Error());
    render(<TrustedDevicesPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Remover este navegador" }));
    await screen.findByRole("alert");
    expect(screen.getByText("Este navegador")).toBeInTheDocument();
    vi.mocked(api.forgetCurrentDevice).mockReturnValue(new Promise(() => {}));
    const button = screen.getByRole("button", { name: "Remover este navegador" });
    fireEvent.click(button); fireEvent.click(button);
    expect(api.forgetCurrentDevice).toHaveBeenCalledTimes(2);
    expect(button).toBeDisabled();
  });
  it("informa recurso desabilitado com lista vazia honesta", async () => {
    vi.mocked(api.listTrustedDevices).mockResolvedValue({ ...data, enabled: false, items: [] });
    render(<TrustedDevicesPanel />);
    await screen.findByText(/Novas concessões e uso de confiança estão desabilitados/);
    expect(screen.getByText("Nenhum dispositivo confiável ativo.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revogar todos os dispositivos" })).not.toBeInTheDocument();
  });
});
