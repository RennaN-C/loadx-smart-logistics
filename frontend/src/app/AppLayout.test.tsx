import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
    updateUser: vi.fn(),
  });
  return logout;
}

function renderLayout(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<p>conteudo da rota</p>} />
          <Route path="settings" element={<p>conteudo das configurações</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

function menu() {
  return screen.getByRole("navigation", { name: "Navegação principal" });
}

describe("AppLayout", () => {
  beforeEach(() => window.localStorage.removeItem("loadx.sidebar-collapsed"));

  it("renderiza o cabeçalho da LoadX e o conteúdo da rota filha", () => {
    signedInAs("ADMIN");
    renderLayout();

    expect(screen.getByText("LOADX", { selector: ".app-brand-label" })).toBeInTheDocument();
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

  it("põe a Frota na Operação, e não nos Cadastros", () => {
    // Situação da frota muda sozinha durante o dia: é acompanhamento, não
    // cadastro. O caminhão em si continua em Cadastros.
    signedInAs("ADMIN");
    renderLayout();

    const grupos = within(menu()).getAllByRole("list");
    expect(within(grupos[2]).getByRole("link", { name: "Frota" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Frota" })).toHaveAttribute("href", "/fleet");
  });

  it("o conferente vê a situação da frota, que ele também lê no backend", () => {
    signedInAs("CHECKER");
    renderLayout();

    expect(screen.getByRole("link", { name: "Frota" })).toBeInTheDocument();
  });

  it("o motorista não vê a frota: o backend responderia 403", () => {
    signedInAs("DRIVER");
    renderLayout();

    expect(screen.queryByRole("link", { name: "Frota" })).not.toBeInTheDocument();
  });

  it("o painel operacional não aparece para o conferente", () => {
    signedInAs("CHECKER");
    renderLayout();

    expect(screen.queryByRole("link", { name: "Painel operacional" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Indicadores" })).toBeInTheDocument();
  });

  it("o gestor chega ao painel operacional e à auditoria", () => {
    signedInAs("LOGISTICS_MANAGER");
    renderLayout();

    expect(screen.getByRole("link", { name: "Painel operacional" })).toHaveAttribute(
      "href",
      "/operations",
    );
    expect(screen.getByRole("link", { name: "Auditoria" })).toHaveAttribute(
      "href",
      "/audit",
    );
  });

  it("esconde a auditoria de conferente e motorista", () => {
    signedInAs("CHECKER");
    const rendered = renderLayout();
    expect(screen.queryByRole("link", { name: "Auditoria" })).not.toBeInTheDocument();

    rendered.unmount();
    signedInAs("DRIVER");
    renderLayout();
    expect(screen.queryByRole("link", { name: "Auditoria" })).not.toBeInTheDocument();
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
  it("recolhe para navegação por ícones sem perder links ou RBAC", () => {
    signedInAs("ADMIN");
    renderLayout();
    fireEvent.click(screen.getByRole("button", { name: "Recolher menu lateral" }));

    const shell = document.querySelector(".app-shell");
    expect(shell).toHaveAttribute("data-sidebar-collapsed", "true");
    expect(screen.getByRole("button", { name: "Expandir menu lateral" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: "Caminhões" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cadastros" })).toHaveAttribute("title", "Cadastros");
    fireEvent.click(screen.getByRole("button", { name: "Cadastros" }));
    expect(shell).toHaveAttribute("data-sidebar-collapsed", "false");
    expect(screen.getByRole("link", { name: "Caminhões" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Recolher menu lateral" }));
    expect(shell).toHaveAttribute("data-sidebar-collapsed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Expandir menu lateral" }));
    expect(shell).toHaveAttribute("data-sidebar-collapsed", "false");
    expect(screen.getByRole("link", { name: "Caminhões" })).not.toHaveAttribute("title");
  });

  it("preserva preferência de sidebar ao remontar a página", () => {
    signedInAs("ADMIN");
    const rendered = renderLayout();
    fireEvent.click(screen.getByRole("button", { name: "Recolher menu lateral" }));
    expect(window.localStorage.getItem("loadx.sidebar-collapsed")).toBe("true");
    rendered.unmount();
    renderLayout();
    expect(screen.getByRole("button", { name: "Expandir menu lateral" })).toBeInTheDocument();
  });

  it("abre a gaveta mobile e fecha com Escape, restaurando a rolagem", () => {
    signedInAs("ADMIN");
    renderLayout();
    const trigger = screen.getByRole("button", { name: "Abrir menu" });
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "true");
    expect(document.body.style.overflow).toBe("hidden");
    expect(screen.getByRole("button", { name: "Fechar menu" })).toHaveFocus();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "false");
    expect(document.body.style.overflow).toBe("");
    expect(trigger).toHaveFocus();
  });

  it("fecha a gaveta ao clicar fora, no botão ou ao navegar", () => {
    signedInAs("ADMIN");
    renderLayout();
    const trigger = screen.getByRole("button", { name: "Abrir menu" });
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("button", { name: "Fechar o menu ao clicar fora" }));
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "false");

    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("button", { name: "Fechar menu" }));
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "false");

    fireEvent.click(trigger);
    fireEvent.click(within(menu()).getByRole("link", { name: "Início" }));
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "false");
  });

  it("não expõe links proibidos dentro do menu mobile", () => {
    signedInAs("DRIVER");
    renderLayout();
    fireEvent.click(screen.getByRole("button", { name: "Abrir menu" }));
    expect(within(menu()).getByRole("link", { name: "Meu perfil" })).toBeInTheDocument();
    expect(within(menu()).queryByRole("link", { name: "Configurações" })).not.toBeInTheDocument();
    expect(within(menu()).queryByRole("link", { name: "Frota" })).not.toBeInTheDocument();
  });


  it("ADMIN abre Configurações no menu existente, com subseções apenas nessa área", () => {
    signedInAs("ADMIN");
    renderLayout();
    expect(within(menu()).queryByRole("link", { name: "Dados da empresa" })).not.toBeInTheDocument();
    fireEvent.click(within(menu()).getByRole("link", { name: "Configurações" }));
    expect(screen.getByText("conteudo das configurações")).toBeInTheDocument();
    expect(within(menu()).getByRole("link", { name: "Configurações" })).toHaveAttribute("aria-expanded", "true");
    expect(within(menu()).getByRole("link", { name: "Dados da empresa" })).toHaveAttribute("href", "/settings#settings-company");
    expect(within(menu()).getByRole("link", { name: "Conta e administração" })).toHaveAttribute("aria-current", "location");
    fireEvent.click(within(menu()).getByRole("link", { name: "Início" }));
    expect(within(menu()).queryByRole("link", { name: "Dados da empresa" })).not.toBeInTheDocument();
  });

  it("expande a sidebar compacta ao selecionar Configurações e marca hash direto", () => {
    signedInAs("ADMIN");
    renderLayout("/settings#settings-integrations");
    expect(within(menu()).getByRole("link", { name: "Integrações e Saúde" })).toHaveAttribute("aria-current", "location");
    fireEvent.click(screen.getByRole("button", { name: "Recolher menu lateral" }));
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-sidebar-collapsed", "true");
    expect(within(menu()).queryByRole("link", { name: "Integrações e Saúde" })).not.toBeInTheDocument();
    fireEvent.click(within(menu()).getByRole("link", { name: "Configurações" }));
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-sidebar-collapsed", "false");
    expect(within(menu()).getByRole("link", { name: "Conta e administração" })).toHaveAttribute("aria-current", "location");
  });

  it("no drawer, primeiro expande Configurações e só fecha ao escolher subseção", () => {
    signedInAs("ADMIN");
    renderLayout();
    fireEvent.click(screen.getByRole("button", { name: "Abrir menu" }));
    fireEvent.click(within(menu()).getByRole("link", { name: "Configurações" }));
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "true");
    expect(within(menu()).getByRole("link", { name: "Dados da empresa" })).toBeInTheDocument();
    fireEvent.click(within(menu()).getByRole("link", { name: "Dados da empresa" }));
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "false");
    expect(within(menu()).getByRole("link", { name: "Dados da empresa" })).toHaveAttribute("aria-current", "location");
  });

  it("não apresenta subseções administrativas para LOGISTICS_MANAGER, CHECKER e DRIVER", () => {
    for (const role of ["LOGISTICS_MANAGER", "CHECKER", "DRIVER"] as const) {
      signedInAs(role);
      const app = renderLayout();
      expect(within(menu()).queryByRole("link", { name: "Configurações" })).not.toBeInTheDocument();
      expect(within(menu()).queryByRole("link", { name: "Conta e administração" })).not.toBeInTheDocument();
      app.unmount();
    }
  });

  it("recolhe e expande Cadastros e Operação com cliques repetidos sem navegar", () => {
    signedInAs("ADMIN");
    renderLayout();
    const cadastros = within(menu()).getByRole("button", { name: "Cadastros" });
    const operacao = within(menu()).getByRole("button", { name: "Operação" });
    expect(cadastros).toHaveAttribute("aria-expanded", "true");
    expect(operacao).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(cadastros);
    expect(cadastros).toHaveAttribute("aria-expanded", "false");
    expect(within(menu()).queryByRole("link", { name: "Caminhões" })).not.toBeInTheDocument();
    expect(within(menu()).getByRole("link", { name: "Pedidos" })).toBeInTheDocument();

    fireEvent.click(operacao);
    expect(operacao).toHaveAttribute("aria-expanded", "false");
    expect(within(menu()).queryByRole("link", { name: "Pedidos" })).not.toBeInTheDocument();
    fireEvent.click(cadastros);
    expect(cadastros).toHaveAttribute("aria-expanded", "true");
    expect(within(menu()).getByRole("link", { name: "Caminhões" })).toHaveAttribute("href", "/trucks");
    fireEvent.click(operacao);
    expect(within(menu()).getByRole("link", { name: "Frota" })).toHaveAttribute("href", "/fleet");
    expect(within(menu()).getByRole("link", { name: "Início" })).toHaveAttribute("aria-current", "page");
  });

  it("fecha Configurações no segundo clique e reabre no terceiro sem sair da página", () => {
    signedInAs("ADMIN");
    renderLayout("/settings#settings-company");
    const parent = within(menu()).getByRole("link", { name: "Configurações" });
    expect(parent).toHaveAttribute("aria-expanded", "true");
    expect(within(menu()).getByRole("link", { name: "Dados da empresa" })).toHaveAttribute("aria-current", "location");
    fireEvent.click(parent);
    expect(parent).toHaveAttribute("aria-expanded", "false");
    expect(within(menu()).queryByRole("link", { name: "Dados da empresa" })).not.toBeInTheDocument();
    expect(screen.getByText("conteudo das configurações")).toBeInTheDocument();

    fireEvent.click(parent);
    expect(parent).toHaveAttribute("aria-expanded", "true");
    expect(within(menu()).getByRole("link", { name: "Dados da empresa" })).toHaveAttribute("aria-current", "location");
  });

  it("abre e fecha os grupos também dentro da gaveta mobile", () => {
    signedInAs("ADMIN");
    renderLayout();
    fireEvent.click(screen.getByRole("button", { name: "Abrir menu" }));
    const cadastros = within(menu()).getByRole("button", { name: "Cadastros" });
    fireEvent.click(cadastros);
    expect(cadastros).toHaveAttribute("aria-expanded", "false");
    expect(within(menu()).queryByRole("link", { name: "Caminhões" })).not.toBeInTheDocument();
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "true");
    fireEvent.click(cadastros);
    expect(within(menu()).getByRole("link", { name: "Caminhões" })).toBeInTheDocument();

    const settings = within(menu()).getByRole("link", { name: "Configurações" });
    fireEvent.click(settings);
    expect(within(menu()).getByRole("link", { name: "Dados da empresa" })).toBeInTheDocument();
    fireEvent.click(settings);
    expect(within(menu()).queryByRole("link", { name: "Dados da empresa" })).not.toBeInTheDocument();
    expect(document.querySelector(".app-shell")).toHaveAttribute("data-mobile-open", "true");
  });
});
