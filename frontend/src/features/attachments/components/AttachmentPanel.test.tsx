import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { downloadAttachment, listAttachments, readAttachmentFile, revokeAttachment, uploadAttachment, type Attachment } from "../api/attachmentsApi";
import { saveBlob } from "../../reports/api/reportsApi";
import { AttachmentPanel } from "./AttachmentPanel";

vi.mock("../api/attachmentsApi", () => ({ listAttachments: vi.fn(), uploadAttachment: vi.fn(), revokeAttachment: vi.fn(), downloadAttachment: vi.fn(), readAttachmentFile: vi.fn() }));
vi.mock("../../reports/api/reportsApi", () => ({ saveBlob: vi.fn() }));
const row: Attachment = { id: "a1", resource_type: "orders", resource_id: "o1", media_type: "image/png", size_bytes: 44, sha256: "hash", status: "ACTIVE", recorded_by: "u1", recorded_at: "2026-10-09T12:00:00Z", revoked_by: null, revoked_at: null };
const page = (items: Attachment[] = []) => ({ items, page: 1, pageSize: 20, total: items.length, totalPages: 1 });
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listAttachments).mockResolvedValue(page());
  vi.mocked(readAttachmentFile).mockResolvedValue("pixels");
  vi.mocked(uploadAttachment).mockResolvedValue(row);
  vi.mocked(revokeAttachment).mockResolvedValue({ ...row, status: "REVOKED" });
});
it("mostra loading e vazio", async () => {
  render(<AttachmentPanel resource="orders" resourceId="o1" canManage />);
  expect(screen.getByText("Carregando anexos…")).toBeInTheDocument();
  expect(await screen.findByText("Nenhum anexo registrado.")).toBeInTheDocument();
});
it("conferente consulta sem ações de gestão", async () => {
  vi.mocked(listAttachments).mockResolvedValue(page([row]));
  render(<AttachmentPanel resource="orders" resourceId="o1" canManage={false} />);
  expect(await screen.findByRole("button", { name: "Baixar anexo" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Enviar anexo" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Remover anexo" })).not.toBeInTheDocument();
});
it("retry mantém event_id e troca de arquivo cria novo evento", async () => {
  vi.mocked(uploadAttachment).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "Rede indisponível"));
  render(<AttachmentPanel resource="orders" resourceId="o1" canManage />);
  await screen.findByText("Nenhum anexo registrado.");
  fireEvent.change(screen.getByLabelText("Arquivo PNG/JPEG"), { target: { files: [new File(["pixels"], "a.png", { type: "image/png" })] } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar anexo" }));
  await screen.findByText("Rede indisponível");
  fireEvent.click(screen.getByRole("button", { name: "Enviar anexo" }));
  await waitFor(() => expect(uploadAttachment).toHaveBeenCalledTimes(2));
  expect(vi.mocked(uploadAttachment).mock.calls[1][2]).toBe(vi.mocked(uploadAttachment).mock.calls[0][2]);
  await waitFor(() => expect(screen.getByRole("button", { name: "Enviar anexo" })).toBeDisabled());
  fireEvent.change(screen.getByLabelText("Arquivo PNG/JPEG"), { target: { files: [new File(["different pixels"], "b.png", { type: "image/png" })] } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar anexo" }));
  await waitFor(() => expect(uploadAttachment).toHaveBeenCalledTimes(3));
  expect(vi.mocked(uploadAttachment).mock.calls[2][2]).not.toBe(vi.mocked(uploadAttachment).mock.calls[0][2]);
});
it("remove após confirmação, preserva revogado e bloqueia download visual", async () => {
  vi.mocked(listAttachments).mockResolvedValueOnce(page([row])).mockResolvedValue(page([{ ...row, status: "REVOKED" }]));
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<AttachmentPanel resource="orders" resourceId="o1" canManage />);
  fireEvent.click(await screen.findByRole("button", { name: "Remover anexo" }));
  await waitFor(() => expect(revokeAttachment).toHaveBeenCalledWith("orders", "o1", "a1"));
  expect(await screen.findByText(/Removido/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Baixar anexo" })).not.toBeInTheDocument();
});
it("download autenticado usa blob e nome interno", async () => {
  vi.mocked(listAttachments).mockResolvedValue(page([row]));
  const blob = new Blob(["bytes"]);
  vi.mocked(downloadAttachment).mockResolvedValue(blob);
  render(<AttachmentPanel resource="orders" resourceId="o1" canManage />);
  fireEvent.click(await screen.findByRole("button", { name: "Baixar anexo" }));
  await waitFor(() => expect(saveBlob).toHaveBeenCalledWith(blob, "a1.png"));
});
it("mostra falha sem mascarar indisponibilidade", async () => {
  vi.mocked(listAttachments).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado"));
  render(<AttachmentPanel resource="orders" resourceId="o1" canManage={false} />);
  expect(await screen.findByText("Acesso negado")).toBeInTheDocument();
});
it("pagina a consulta", async () => {
  vi.mocked(listAttachments).mockResolvedValue({ ...page([row]), total: 22, totalPages: 2 });
  render(<AttachmentPanel resource="orders" resourceId="o1" canManage />);
  await screen.findByRole("button", { name: "Baixar anexo" });
  fireEvent.click(screen.getByRole("button", { name: /Próxima/ }));
  await waitFor(() => expect(listAttachments).toHaveBeenCalledWith("orders", "o1", { page: 2 }));
});
