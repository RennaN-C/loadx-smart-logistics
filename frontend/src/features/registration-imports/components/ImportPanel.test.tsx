import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { confirmImport, downloadImportTemplate, getImport, listImports, previewImport, readCsvFile, type ImportPreview, type ImportResult } from "../api/importsApi";
import { saveBlob } from "../../reports/api/reportsApi";
import { ImportPanel } from "./ImportPanel";
vi.mock("../api/importsApi", () => ({ confirmImport: vi.fn(), downloadImportTemplate: vi.fn(), getImport: vi.fn(), listImports: vi.fn(), previewImport: vi.fn(), readCsvFile: vi.fn() }));
vi.mock("../../reports/api/reportsApi", () => ({ saveBlob: vi.fn() }));
vi.mock("../../audit/components/AuditTrail", () => ({ AuditTrail: () => <p>Trilha de auditoria</p> }));
const file = { file_name: "fixture.csv", content_base64: "Y3N2" };
const view: ImportPreview = { entity_type: "products", sha256: "hash", row_count: 1, valid_count: 1, can_confirm: true, errors: [], rows: [{ line: 2, data: { code: "CX-A", name: "Caixa fictícia" } }] };
const result: ImportResult = { id: "i1", entity_type: "products", recorded_by: "u1", recorded_at: "2026-10-09T00:00:00Z", sha256: "hash", status: "COMPLETED", row_count: 1, created_count: 1, rejected_count: 0, errors: [], records: [{ line: 2, id: "p1" }] };
const saved = vi.fn(async () => undefined);
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listImports).mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0, totalPages: 0 });
  vi.mocked(readCsvFile).mockResolvedValue(file);
  vi.mocked(previewImport).mockResolvedValue(view);
  vi.mocked(confirmImport).mockResolvedValue(result);
  vi.mocked(getImport).mockResolvedValue(result);
});
async function generatePreview() {
  fireEvent.change(screen.getByLabelText("Arquivo CSV"), { target: { files: [new File(["csv"], "fixture.csv")] } });
  fireEvent.click(screen.getByRole("button", { name: "Validar e gerar prévia" }));
  await screen.findByText("Caixa fictícia");
}
it("carrega histórico vazio sem importar ou prévia automaticamente", async () => {
  render(<ImportPanel entity="products" onImported={saved} />);
  expect(screen.getByText("Carregando histórico…")).toBeInTheDocument();
  expect(await screen.findByText("Nenhuma importação registrada.")).toBeInTheDocument();
  expect(confirmImport).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "Confirmar importação" })).not.toBeInTheDocument();
});
it("mostra prévia e exige confirmação explícita antes da criação", async () => {
  render(<ImportPanel entity="products" onImported={saved} />);
  await generatePreview();
  expect(confirmImport).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirmar importação" }));
  await screen.findByText("Importação concluída");
  expect(confirmImport).toHaveBeenCalledWith("products", file, "hash", expect.any(String));
  expect(saved).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Linha 2: p1")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Confirmar importação" })).toBeDisabled();
});
it("erros de linha/campo impedem confirmação", async () => {
  vi.mocked(previewImport).mockResolvedValue({ ...view, can_confirm: false, valid_count: 0, errors: [{ line: 2, field: "weight_kg", code: "greater_than", message: "Peso inválido" }] });
  render(<ImportPanel entity="products" onImported={saved} />);
  await generatePreview();
  expect(screen.getByText(/Linha 2 · weight_kg: Peso inválido/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Confirmar importação" })).toBeDisabled();
  expect(confirmImport).not.toHaveBeenCalled();
});
it("trocar arquivo limpa prévia para evitar confirmação desatualizada", async () => {
  render(<ImportPanel entity="products" onImported={saved} />);
  await generatePreview();
  fireEvent.change(screen.getByLabelText("Arquivo CSV"), { target: { files: [new File(["other"], "other.csv")] } });
  expect(screen.queryByText("Caixa fictícia")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Confirmar importação" })).not.toBeInTheDocument();
});
it("retry de resposta incerta conserva evento e não duplica importação", async () => {
  vi.mocked(confirmImport).mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "Resposta indisponível"));
  render(<ImportPanel entity="products" onImported={saved} />);
  await generatePreview();
  fireEvent.click(screen.getByRole("button", { name: "Confirmar importação" }));
  await screen.findByText("Resposta indisponível");
  fireEvent.click(screen.getByRole("button", { name: "Confirmar importação" }));
  await screen.findByText("Importação concluída");
  expect(vi.mocked(confirmImport).mock.calls[0][3]).toBe(vi.mocked(confirmImport).mock.calls[1][3]);
  expect(saved).toHaveBeenCalledTimes(1);
});
it("rejeição por conflito após prévia mostra zero criados", async () => {
  vi.mocked(confirmImport).mockResolvedValue({ ...result, status: "REJECTED", created_count: 0, rejected_count: 1, records: [], errors: [{ line: 2, field: "code", code: "DUPLICATE_EXISTING", message: "Duplicidade" }] });
  render(<ImportPanel entity="products" onImported={saved} />);
  await generatePreview();
  fireEvent.click(screen.getByRole("button", { name: "Confirmar importação" }));
  await screen.findByText("Arquivo rejeitado");
  expect(screen.getByText("0 cadastros criados; 1 linhas rejeitadas.")).toBeInTheDocument();
  expect(saved).not.toHaveBeenCalled();
});
it("baixa template privado e consulta resultado histórico", async () => {
  const blob = new Blob(["code,name"]);
  vi.mocked(downloadImportTemplate).mockResolvedValue(blob);
  vi.mocked(listImports).mockResolvedValue({ items: [result], page: 1, pageSize: 20, total: 22, totalPages: 2 });
  render(<ImportPanel entity="products" onImported={saved} />);
  fireEvent.click(screen.getByRole("button", { name: "Baixar modelo CSV" }));
  await waitFor(() => expect(saveBlob).toHaveBeenCalledWith(blob, "products-modelo.csv"));
  fireEvent.click(await screen.findByRole("button", { name: "Ver resultado" }));
  await screen.findByText("Importação concluída");
  expect(getImport).toHaveBeenCalledWith("i1");
  fireEvent.click(screen.getByRole("button", { name: /Próxima/ }));
  await waitFor(() => expect(listImports).toHaveBeenCalledWith("products", { page: 2 }));
});
it("falha no histórico tem feedback e preview mantém texto escapado", async () => {
  vi.mocked(listImports).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "Acesso negado"));
  vi.mocked(previewImport).mockResolvedValue({ ...view, rows: [{ line: 2, data: { code: "CX-A", name: "<img src=x onerror=alert(1)>" } }] });
  const { container } = render(<ImportPanel entity="products" onImported={saved} />);
  await screen.findByText("Acesso negado");
  fireEvent.change(screen.getByLabelText("Arquivo CSV"), { target: { files: [new File(["csv"], "fixture.csv")] } });
  fireEvent.click(screen.getByRole("button", { name: "Validar e gerar prévia" }));
  await screen.findByText("<img src=x onerror=alert(1)>");
  expect(container.querySelector("img")).toBeNull();
});
