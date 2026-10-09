import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { listDocuments, listDocumentPolicies, saveDocument, setDocumentPolicy, type TruckDocument } from "../api/documentsApi";
import type { Truck } from "../types";
import { DocumentsPanel } from "./DocumentsPanel";
vi.mock("../../auth/hooks/useAuth"); vi.mock("../api/documentsApi");
const truck: Truck = { id: "t1", plate: "ABC1D23", model: "Baú", internalWidthCm: 100, internalHeightCm: 100, internalLengthCm: 100, maxWeightKg: 1000, active: true, createdAt: "2026-01-01T00:00:00Z" };
const record: TruckDocument = { id: "d1", truck_id: "t1", kind: "CRLV", reference: "REF-FICTICIA", issued_at: "2020-01-01T00:00:00Z", expires_at: "2021-01-01T00:00:00Z", file_reference: null, superseded_at: null, status: "EXPIRED", created_at: "2020-01-01T00:00:00Z" };
const changed = vi.fn().mockResolvedValue(undefined);
function show(value = truck) { render(<DocumentsPanel truck={value} onChanged={changed} />); }
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user: { id: "u1", name: "Gestor", email: "manager@example.test", role: "LOGISTICS_MANAGER", active: true, createdAt: "2026-01-01T00:00:00Z" }, status: "authenticated", login: vi.fn(), logout: vi.fn() });
  vi.mocked(listDocuments).mockResolvedValue({ items: [record], page: 1, pageSize: 20, total: 1, totalPages: 1 });
  vi.mocked(listDocumentPolicies).mockResolvedValue([]);
  vi.mocked(saveDocument).mockResolvedValue(record);
  vi.mocked(setDocumentPolicy).mockResolvedValue({ id: "p1", truck_id: "t1", kind: "CRLV", required: true });
});
it("destaca vencimento sem inferir bloqueio obrigatório", async () => {
  show(); expect(await screen.findByText("Vencido")).toBeInTheDocument();
  expect(screen.getByLabelText("Exigir CRLV")).not.toBeChecked();
  expect(screen.getByText(/REF-FICTICIA/)).toBeInTheDocument();
});
it("configura política explícita e atualiza a consulta", async () => {
  show(); const input = await screen.findByLabelText("Exigir CRLV"); fireEvent.click(input);
  await waitFor(() => expect(setDocumentPolicy).toHaveBeenCalledWith("t1", "CRLV", true));
  await waitFor(() => expect(input).toBeChecked()); expect(changed).toHaveBeenCalled();
});
it("cadastra documento com datas opcionais e referência de arquivo", async () => {
  show(); fireEvent.click(await screen.findByRole("button", { name: "Novo documento" }));
  fireEvent.change(screen.getByLabelText("Número ou referência"), { target: { value: "SEG-FICTICIO" } });
  fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "INSURANCE" } });
  fireEvent.click(screen.getByRole("button", { name: "Registrar documento" }));
  await waitFor(() => expect(saveDocument).toHaveBeenCalledWith("t1", { kind: "INSURANCE", reference: "SEG-FICTICIO", issued_at: null, expires_at: null, file_reference: null }, undefined));
});
it("renova preservando a versão anterior e fixando tipo", async () => {
  show(); fireEvent.click(await screen.findByRole("button", { name: "Renovar CRLV" }));
  expect(screen.getByLabelText("Tipo")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Validade"), { target: { value: "2099-01-01T10:00" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirmar renovação" }));
  await waitFor(() => expect(saveDocument).toHaveBeenCalledWith("t1", expect.objectContaining({ kind: "CRLV", expires_at: expect.stringMatching(/2099-01-01T/) }), "d1"));
});
it("conferente consulta sem alterar documentos ou política", async () => {
  const auth = vi.mocked(useAuth).getMockImplementation()!(); vi.mocked(useAuth).mockReturnValue({ ...auth, user: { ...auth.user!, role: "CHECKER" } });
  show(); await screen.findByText("Vencido");
  expect(screen.queryByRole("button", { name: "Novo documento" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Renovar CRLV" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("Exigir CRLV")).toBeDisabled();
});
it("arquivado preserva histórico com gestão desabilitada", async () => {
  show({ ...truck, active: false }); await screen.findByText("Vencido");
  expect(screen.queryByRole("button", { name: "Novo documento" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("Exigir CRLV")).toBeDisabled();
});
it("exibe vazio e erro de consulta", async () => {
  vi.mocked(listDocuments).mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0, totalPages: 0 });
  show(); expect(await screen.findByText("Nenhum documento registrado.")).toBeInTheDocument();
});
it("apresenta falha de escrita sem atualizar consulta", async () => {
  vi.mocked(setDocumentPolicy).mockRejectedValue(new ApiError("ERROR", "Política indisponível."));
  show(); fireEvent.click(await screen.findByLabelText("Exigir CRLV"));
  expect(await screen.findByText("Política indisponível.")).toBeInTheDocument(); expect(changed).not.toHaveBeenCalled();
});
it("apresenta falhas de leitura", async () => {
  vi.mocked(listDocuments).mockRejectedValue(new ApiError("ERROR", "Consulta indisponível."));
  vi.mocked(listDocumentPolicies).mockRejectedValue(new ApiError("ERROR", "Erro"));
  show(); expect(await screen.findByText("Consulta indisponível.")).toBeInTheDocument();
  expect(await screen.findByText("Não foi possível consultar a política documental.")).toBeInTheDocument();
});
it("identifica versões substituídas e vencimento próximo", async () => {
  vi.mocked(listDocuments).mockResolvedValue({ items: [{ ...record, status: "SUPERSEDED", superseded_at: "2026-01-01T00:00:00Z" }, { ...record, id: "d2", status: "EXPIRING" }], page: 1, pageSize: 20, total: 2, totalPages: 1 });
  show(); expect(await screen.findByText("Substituído")).toBeInTheDocument(); expect(screen.getByText("Vence em até 30 dias")).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Renovar CRLV" })).toHaveLength(1);
});
