import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { makePage } from "../../../tests/makePage";
import { getProfile, listProfiles, permissionCatalog, type AccessProfile } from "../api/profilesApi";
import { ProfileAccessSummary } from "./ProfileAccessSummary";

vi.mock("../api/profilesApi");
const PROFILE: AccessProfile = { id: "p1", name: "Consulta da operação", description: "Acompanhamento de frota", active: true, version: 3, permissions: ["loadx.trucks.read"], system_role: null, user_count: 2 };
const CATALOG = [{ code: "loadx.trucks.read", module: "trucks", label: "Consultar caminhões", delegable: true, classification: "delegable" }];
beforeEach(() => { vi.resetAllMocks(); vi.mocked(permissionCatalog).mockResolvedValue(CATALOG); vi.mocked(getProfile).mockResolvedValue(PROFILE); vi.mocked(listProfiles).mockResolvedValue(makePage([{ ...PROFILE, name: "Conferente", system_role: "CHECKER" }])); });

describe("resumo real da atribuição de acesso", () => {
  it("consulta perfil fixo no contrato público sem inventar sua projeção", async () => {
    render(<ProfileAccessSummary role="CHECKER" profileId={null} />);
    const summary = await screen.findByRole("region", { name: "Resumo de acesso selecionado" });
    expect(within(summary).getByText("Conferente")).toBeInTheDocument();
    expect(within(summary).getByText("Ativo · 1 permissões")).toBeInTheDocument();
    expect(listProfiles).toHaveBeenCalledWith({ page: 1, pageSize: 4 });
    expect(getProfile).not.toHaveBeenCalled();
    expect(screen.getByText(/limite a planos aprovados/)).toBeInTheDocument();
  });
  it("consulta selecionado fora da página e revela ações por módulo sem códigos", async () => {
    render(<ProfileAccessSummary role="CUSTOM" profileId="p1" />);
    const summary = await screen.findByRole("region", { name: "Resumo de acesso selecionado" });
    expect(getProfile).toHaveBeenCalledWith("p1");
    expect(within(summary).getByText("Acompanhamento de frota")).toBeInTheDocument();
    expect(within(summary).getByText("Consultar caminhões")).not.toBeVisible();
    fireEvent.click(within(summary).getByText("Ver permissões"));
    const module = summary.querySelector(".access-permission-modules summary")!;
    fireEvent.click(module);
    expect(within(summary).getByText("Consultar caminhões")).toBeVisible();
    expect(summary).not.toHaveTextContent("loadx.");
  });
  it("troca de seleção ignora resposta atrasada e não associa grants ao usuário", async () => {
    let resolveFirst!: (profile: AccessProfile) => void;
    vi.mocked(getProfile).mockReturnValueOnce(new Promise((resolve) => { resolveFirst = resolve; }));
    const view = render(<ProfileAccessSummary role="CUSTOM" profileId="p1" />);
    view.rerender(<ProfileAccessSummary role="CUSTOM" profileId="p2" />);
    await screen.findByRole("region", { name: "Resumo de acesso selecionado" });
    resolveFirst({ ...PROFILE, name: "Resposta antiga" });
    await waitFor(() => expect(screen.queryByText("Resposta antiga")).not.toBeInTheDocument());
  });
  it("distingue sem seleção, consulta, falha e nova tentativa", async () => {
    vi.mocked(getProfile).mockRejectedValueOnce(new Error("RESPOSTA PRIVADA"));
    const view = render(<ProfileAccessSummary role="CUSTOM" profileId={null} />);
    expect(screen.getByText(/Selecione um perfil/)).toBeInTheDocument();
    expect(getProfile).not.toHaveBeenCalled();
    view.rerender(<ProfileAccessSummary role="CUSTOM" profileId="p1" />);
    expect(screen.getByText("Consultando acesso do perfil…")).toBeInTheDocument();
    await screen.findByRole("alert");
    expect(screen.queryByText("RESPOSTA PRIVADA")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Consultar novamente" }));
    await screen.findByRole("region", { name: "Resumo de acesso selecionado" });
  });
});
