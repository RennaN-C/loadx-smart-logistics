import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { approveDocumentType, listDocuments, listDocumentTypes, listDocumentPolicies, saveDocument, setDocumentPolicy, type DriverDocument } from "../api/documentsApi";
import { DocumentsPanel } from "./DocumentsPanel";
vi.mock("../../auth/hooks/useAuth"); vi.mock("../api/documentsApi");
const driver = { id: "m1", name: "Motorista fictício", licenseCategory: "D", active: true, createdAt: "2026-01-01T00:00:00Z" };
const record: DriverDocument = { id: "d1", driver_id: "m1", document_type_id: "cnh", reference: "12345678900", category: "D", issued_at: null, expires_at: "2020-01-01T00:00:00Z", created_at: "2019-01-01T00:00:00Z", superseded_at: null, status: "EXPIRED" };
const changed = vi.fn().mockResolvedValue(undefined);
function show(active = true) { render(<DocumentsPanel driver={{ ...driver, active }} onChanged={changed}/>); }
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user: { id: "u1", name: "Gestor", email: "manager@example.test", role: "LOGISTICS_MANAGER", active: true, createdAt: "2026-01-01T00:00:00Z" }, status: "authenticated", login: vi.fn(), logout: vi.fn() });
  vi.mocked(listDocuments).mockResolvedValue({ items: [record], page: 1, pageSize: 20, total: 1, totalPages: 1 });
  vi.mocked(listDocumentTypes).mockResolvedValue([{ id: "cnh", code: "CNH", name: "CNH" }]); vi.mocked(listDocumentPolicies).mockResolvedValue([]);
  vi.mocked(saveDocument).mockResolvedValue(record); vi.mocked(setDocumentPolicy).mockResolvedValue({ id: "p1", driver_id: "m1", document_type_id: "cnh", required: true, allowed_categories: ["D"] });
  vi.mocked(approveDocumentType).mockResolvedValue({ id: "t2", code: "LOCAL", name: "Documento local" });
});
it("distingue CNH vencida e consulta política sem assumir obrigatoriedade", async () => {
  show(); expect(await screen.findByText("Vencido")).toBeInTheDocument(); expect(await screen.findByLabelText("Exigir CNH")).not.toBeChecked();
});
it("salva categoria aceita e obrigatoriedade explícitas", async () => {
  show(); fireEvent.click(await screen.findByLabelText("Exigir CNH")); fireEvent.click(screen.getByLabelText("Aceitar D")); fireEvent.click(screen.getByRole("button", { name: "Salvar política CNH" }));
  await waitFor(() => expect(setDocumentPolicy).toHaveBeenCalledWith("m1", "cnh", true, ["D"])); expect(changed).toHaveBeenCalled();
});
it("renova CNH preservando tipo e enviando validade UTC", async () => {
  show(); fireEvent.click(await screen.findByRole("button", { name: "Renovar documento" })); expect(screen.getByLabelText("Tipo aprovado")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Validade"), { target: { value: "2099-01-01T10:00" } }); fireEvent.click(screen.getByRole("button", { name: "Confirmar renovação" }));
  await waitFor(() => expect(saveDocument).toHaveBeenCalledWith("m1", expect.objectContaining({ category: "D", expires_at: expect.stringContaining("2099-01-01T") }), "d1"));
});
it("aprova tipo adicional sem inventar exigência automática", async () => {
  show(); fireEvent.change(await screen.findByLabelText("Código do tipo adicional"), { target: { value: "local" } }); fireEvent.change(screen.getByLabelText("Nome do tipo adicional"), { target: { value: "Documento local" } }); fireEvent.click(screen.getByRole("button", { name: "Aprovar tipo adicional" }));
  await waitFor(() => expect(approveDocumentType).toHaveBeenCalledWith("LOCAL", "Documento local")); expect(await screen.findByLabelText("Exigir Documento local")).not.toBeChecked();
});
it("preserva consulta de arquivados com ações desabilitadas", async () => {
  show(false); await screen.findByText("Vencido"); expect(screen.queryByRole("button", { name: "Renovar documento" })).not.toBeInTheDocument(); expect(screen.queryByRole("button", { name: "Aprovar tipo adicional" })).not.toBeInTheDocument(); expect(await screen.findByLabelText("Exigir CNH")).toBeDisabled();
});
it("não trata falha de catálogo como política desligada", async () => {
  vi.mocked(listDocumentTypes).mockRejectedValue(new Error("unavailable")); show(); expect(await screen.findByText("Não foi possível consultar tipos e políticas.")).toBeInTheDocument(); expect(screen.queryByLabelText("Exigir CNH")).not.toBeInTheDocument();
});
it("apresenta vazio, vencimento próximo e falha de escrita", async () => {
  vi.mocked(listDocuments).mockResolvedValue({ items: [{ ...record, status: "EXPIRING" }], page: 1, pageSize: 20, total: 1, totalPages: 1 }); vi.mocked(setDocumentPolicy).mockRejectedValue(new ApiError("ERROR", "Política indisponível."));
  show(); expect(await screen.findByText("Vence em até 30 dias")).toBeInTheDocument(); fireEvent.click(await screen.findByRole("button", { name: "Salvar política CNH" })); expect(await screen.findByText("Política indisponível.")).toBeInTheDocument(); expect(changed).not.toHaveBeenCalled();
});
