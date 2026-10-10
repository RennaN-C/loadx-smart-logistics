import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../types/api";
import { getCompanyProfile, updateCompanyProfile, type CompanyProfile } from "../api/companyProfileApi";
import { CompanyProfileForm } from "./CompanyProfileForm";
vi.mock("../api/companyProfileApi");
vi.mock("../../audit/components/AuditTrail", () => ({ AuditTrail: () => <p>Histórico institucional</p> }));
const PROFILE: CompanyProfile = { id: "company-id", legal_name: "Empresa real Ltda", display_name: "Empresa real", cnpj: "11222333000181", phone: "11900000000", email: "contato@example.test", logo_reference: "https://example.test/logo.svg", created_at: "2026-10-09T00:00:00Z", updated_at: "2026-10-09T00:00:00Z" };
beforeEach(() => { vi.resetAllMocks(); vi.mocked(getCompanyProfile).mockResolvedValue(PROFILE); vi.mocked(updateCompanyProfile).mockResolvedValue(PROFILE); });
describe("OC91: dados institucionais", () => {
  it("consulta dados reais sem edição automática", async () => {
    render(<CompanyProfileForm />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando");
    expect(await screen.findByLabelText("Nome empresarial")).toHaveValue(PROFILE.legal_name);
    expect(screen.getByLabelText("Nome empresarial")).toHaveAttribute("readonly");
    expect(updateCompanyProfile).not.toHaveBeenCalled();
    expect(screen.getByText("Histórico institucional")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
  it("cadastro vazio não inventa dados nem grava em consulta", async () => {
    vi.mocked(getCompanyProfile).mockResolvedValue(null);
    render(<CompanyProfileForm />);
    await screen.findByRole("button", { name: "Cadastrar dados da empresa" });
    expect(screen.getByLabelText("Nome empresarial")).toHaveValue("");
    expect(updateCompanyProfile).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar dados da empresa" }));
    expect(screen.getByLabelText("Nome empresarial")).toBeRequired();
  });
  it("salva, confirma e reconsulta após remontar como F5", async () => {
    const updated = { ...PROFILE, display_name: "Novo nome", email: null };
    vi.mocked(updateCompanyProfile).mockResolvedValue(updated);
    const view = render(<CompanyProfileForm />);
    fireEvent.click(await screen.findByRole("button", { name: "Editar dados da empresa" }));
    fireEvent.change(screen.getByLabelText("Nome de exibição"), { target: { value: " Novo nome " } });
    fireEvent.change(screen.getByLabelText("E-mail institucional"), { target: { value: "" } });
    fireEvent.submit(screen.getByRole("form"));
    await screen.findByText("Dados da empresa salvos com sucesso.");
    expect(updateCompanyProfile).toHaveBeenCalledWith({ legal_name: PROFILE.legal_name, display_name: "Novo nome", cnpj: PROFILE.cnpj, phone: PROFILE.phone, email: null, logo_reference: PROFILE.logo_reference });
    view.unmount(); vi.mocked(getCompanyProfile).mockResolvedValue(updated);
    render(<CompanyProfileForm />);
    expect(await screen.findByLabelText("Nome de exibição")).toHaveValue("Novo nome");
    expect(getCompanyProfile).toHaveBeenCalledTimes(2);
  });
  it("cancelar restaura dados e não chama API", async () => {
    render(<CompanyProfileForm />);
    fireEvent.click(await screen.findByRole("button", { name: "Editar dados da empresa" }));
    fireEvent.change(screen.getByLabelText("Nome empresarial"), { target: { value: "Descartar" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.getByLabelText("Nome empresarial")).toHaveValue(PROFILE.legal_name);
    expect(updateCompanyProfile).not.toHaveBeenCalled();
  });
  it("erro de consulta permite tentar novamente sem formulário fictício", async () => {
    vi.mocked(getCompanyProfile).mockRejectedValueOnce(new Error("offline"));
    render(<CompanyProfileForm />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível consultar");
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByLabelText("Nome empresarial")).toHaveValue(PROFILE.legal_name);
  });
  it("erro de campo mantém rascunho e foca controle inválido", async () => {
    vi.mocked(updateCompanyProfile).mockRejectedValue(new ApiError("VALIDATION_ERROR", "Dados inválidos", [{ field: "cnpj", type: "value_error", message: "Value error, Informe um CNPJ válido." }], 422));
    render(<CompanyProfileForm />);
    fireEvent.click(await screen.findByRole("button", { name: "Editar dados da empresa" }));
    fireEvent.change(screen.getByLabelText("CNPJ"), { target: { value: "123" } });
    fireEvent.submit(screen.getByRole("form"));
    await screen.findByRole("alert");
    expect(screen.getByLabelText("CNPJ")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("CNPJ")).toHaveAccessibleDescription("Informe um CNPJ válido.");
    await waitFor(() => expect(screen.getByLabelText("CNPJ")).toHaveFocus());
    expect(screen.getByLabelText("CNPJ")).toHaveValue("123");
  });
  it.each([401,403,500])("falha HTTP %s não confirma gravação", async (status) => {
    vi.mocked(updateCompanyProfile).mockRejectedValue(new ApiError("FAILED", "Falha administrativa", [], status));
    render(<CompanyProfileForm />);
    fireEvent.click(await screen.findByRole("button", { name: "Editar dados da empresa" }));
    fireEvent.submit(screen.getByRole("form"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Falha administrativa");
    expect(screen.queryByText("Dados da empresa salvos com sucesso.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeEnabled();
  });
  it("envio em andamento bloqueia submissão repetida", async () => {
    vi.mocked(updateCompanyProfile).mockReturnValue(new Promise(() => {}));
    render(<CompanyProfileForm />);
    fireEvent.click(await screen.findByRole("button", { name: "Editar dados da empresa" }));
    fireEvent.submit(screen.getByRole("form"));
    expect(screen.getByRole("button", { name: "Salvando…" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeDisabled();
    fireEvent.submit(screen.getByRole("form"));
    expect(updateCompanyProfile).toHaveBeenCalledOnce();
  });
});
