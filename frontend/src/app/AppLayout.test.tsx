import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { Role } from "../features/auth/types";
import { useAuth } from "../features/auth/hooks/useAuth";
import { AppLayout } from "./AppLayout";

vi.mock("../features/auth/hooks/useAuth");

const AUTHENTICATED_USER = {
  id: "1",
  name: "Ana Souza",
  email: "ana@example.test",
  role: "ADMIN" as const,
  active: true,
  createdAt: "2026-08-01T00:00:00Z",
};

function signedInAs(role: Role, logout = vi.fn()) {
  vi.mocked(useAuth).mockReturnValue({
    status: "authenticated",
    user: { ...AUTHENTICATED_USER, role },
    login: vi.fn(),
    logout,
  });
  return logout;
}

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<p>conteudo da rota</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

function menu() {
  return screen.getByRole("navigation", { name: "Navegação principal" });
}

describe("AppLayout", () => {
  it("renderiza o cabeçalho da LoadX e o conteúdo da rota filha", () => {
    signedInAs("ADMIN");
    renderLayout();

    expect(screen.getByText("LOADX")).toBeInTheDocument();
    expect(screen.getByText("conteudo da rota")).toBeInTheDocument();
  });

  it("mostra o nome e o perfil do usuário autenticado e permite sair", () => {
    const logout = signedInAs("ADMIN");
    renderLayout();

    expect(screen.getByText("Ana Souza")).toBeInTheDocument();
    expect(screen.getByText("Administrador")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    expect(logout).toHaveBeenCalledOnce();
  });

  it("agrupa os itens do menu por natureza da operação", () => {
    signedInAs("ADMIN");
    renderLayout();

    const grupos = within(menu()).getAllByRole("list");
    // o primeiro grupo é o Início, que não tem título
    expect(within(grupos[1]).getByRole("link", { name: "Caminhões" })).toBeInTheDocument();
    expect(within(grupos[2]).getByRole("link", { name: "Pedidos" })).toBeInTheDocument();
    expect(screen.getByText("Cadastros")).toBeInTheDocument();
    expect(screen.getByText("Operação")).toBeInTheDocument();
  });

  it("esconde dados pessoais do conferente sem derrubar o grupo inteiro", () => {
    signedInAs("CHECKER");
    renderLayout();

    expect(screen.queryByRole("link", { name: "Clientes e motoristas" })).not.toBeInTheDocument();
    // Caminhões e Produtos continuam lá, então o título tem que ficar
    expect(screen.getByRole("link", { name: "Caminhões" })).toBeInTheDocument();
    expect(screen.getByText("Cadastros")).toBeInTheDocument();
  });

  it("não deixa título de grupo órfão quando o perfil não lê nada dele", () => {
    signedInAs("DRIVER");
    renderLayout();

    expect(screen.getByRole("link", { name: "Início" })).toBeInTheDocument();
    expect(screen.queryByText("Cadastros")).not.toBeInTheDocument();
    expect(screen.queryByText("Operação")).not.toBeInTheDocument();
  });

  it("marca só a tela atual como ativa", () => {
    signedInAs("ADMIN");
    renderLayout();

    // `end` na raiz: sem ele o Início casaria por prefixo em toda rota
    expect(screen.getByRole("link", { name: "Início" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Caminhões" })).not.toHaveAttribute("aria-current");
  });

  it("oferece atalho para pular o menu, que vem antes do conteúdo no DOM", () => {
    signedInAs("ADMIN");
    renderLayout();

    const atalho = screen.getByRole("link", { name: "Pular para o conteúdo" });
    expect(atalho).toHaveAttribute("href", "#conteudo");
    expect(document.getElementById("conteudo")).not.toBeNull();
  });
});
