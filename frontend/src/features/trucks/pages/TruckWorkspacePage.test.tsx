import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "../../auth/hooks/useAuth";
import { listTrucks, listTruckOperationalStatus } from "../api/trucksApi";
import { listDocuments, listDocumentPolicies } from "../api/documentsApi";
import { listMaintenances } from "../api/maintenanceApi";
import { makePage } from "../../../tests/makePage";
import { TruckWorkspacePage } from "./TruckWorkspacePage";
vi.mock("../../auth/hooks/useAuth");
vi.mock("../api/trucksApi");
vi.mock("../api/documentsApi");
vi.mock("../api/maintenanceApi");
const TRUCK = { id: "truck-test", plate: "ABC1D23", model: "Baú de teste", active: true, internalWidthCm: 240, internalHeightCm: 260, internalLengthCm: 600, maxWeightKg: 8000, createdAt: "2026-01-01T00:00:00Z" };
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(useAuth).mockReturnValue({ status: "authenticated", user: { id: "user-test", name: "Admin teste", email: "admin@example.test", role: "ADMIN", active: true, createdAt: "2026-01-01T00:00:00Z" }, login: vi.fn(), logout: vi.fn(), updateUser: vi.fn() });
  vi.mocked(listTrucks).mockResolvedValue(makePage([TRUCK]));
  vi.mocked(listTruckOperationalStatus).mockResolvedValue(makePage([{ id: TRUCK.id, plate: TRUCK.plate, model: TRUCK.model, active: true, hasOperationConflict: false, available: true }]));
  vi.mocked(listDocuments).mockResolvedValue(makePage([]));
  vi.mocked(listDocumentPolicies).mockResolvedValue([]);
  vi.mocked(listMaintenances).mockResolvedValue(makePage([]));
});
function page(path = "/trucks") { return render(<MemoryRouter initialEntries={[path]}><TruckWorkspacePage /></MemoryRouter>); }
describe("Caminhões e frota", () => {
  it("inicia em veículos e consulta disponibilidade apenas ao abrir a aba", async () => {
    page(); await screen.findByText(TRUCK.plate);
    expect(listTruckOperationalStatus).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("link", { name: "Disponibilidade" }));
    expect(await screen.findByText("Disponível")).toBeVisible();
    expect(screen.getByRole("link", { name: "Disponibilidade" })).toHaveAttribute("aria-current", "location");
    expect(screen.getByText(/disponíveis nesta página/)).toBeVisible();
  });
  it("acesso direto abre disponibilidade e mantém o filtro baseado no backend", async () => {
    page("/trucks?tab=availability");
    await screen.findByText("Disponível");
    fireEvent.change(screen.getByLabelText("Filtrar por disponibilidade"), { target: { value: "unavailable" } });
    expect(screen.getByText("Nenhum caminhão nesta situação, nesta página.")).toBeVisible();
  });
  it("abre a documentação da frota por veículo sem inventar uma listagem global", async () => {
    page("/trucks?tab=documents");
    expect(await screen.findByRole("heading", { name: `Documentos de ${TRUCK.plate}` })).toBeVisible();
    expect(screen.getByRole("combobox", { name: "Veículo" })).toHaveValue(TRUCK.id);
    expect(screen.getByText(/consulta documentos por veículo/i)).toBeVisible();
    expect(listDocuments).toHaveBeenCalledWith(TRUCK.id, expect.anything());
  });
  it("preserva rascunho do cadastro ao trocar abas", async () => {
    page(); await screen.findByText(TRUCK.plate);
    fireEvent.click(screen.getByRole("button", { name: "Novo caminhão" }));
    const input = screen.getByLabelText(/^Placa$/i);
    fireEvent.change(input, { target: { value: "XYZ9A88" } });
    fireEvent.click(screen.getByRole("link", { name: "Disponibilidade" }));
    await screen.findByText("Disponível");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.body.style.overflow).not.toBe("hidden");
    fireEvent.click(screen.getByRole("link", { name: "Veículos" }));
    expect(screen.getByLabelText(/^Placa$/i)).toHaveValue("XYZ9A88");
  });
  it("mantém edição, documentos e manutenções associados ao veículo", async () => {
    page(); await screen.findByText(TRUCK.plate);
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    expect(screen.getByLabelText(/^Placa$/i)).toHaveValue(TRUCK.plate);
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    fireEvent.click(screen.getByRole("button", { name: "Documentos" }));
    await screen.findByText("Nenhum documento registrado.");
    expect(listDocuments).toHaveBeenCalledWith(TRUCK.id, expect.anything());
    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
    fireEvent.click(screen.getByRole("button", { name: "Manutenções" }));
    await screen.findByText("Nenhuma manutenção registrada.");
    expect(listMaintenances).toHaveBeenCalledWith(TRUCK.id, expect.anything());
    await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
  });
});
