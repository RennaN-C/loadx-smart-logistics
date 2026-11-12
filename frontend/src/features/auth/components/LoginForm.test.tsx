import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { useAuth } from "../hooks/useAuth";
import { LoginForm } from "./LoginForm";
import { mapLoginErrorToMessage } from "./loginErrorMessages";

vi.mock("../hooks/useAuth");

describe("mapLoginErrorToMessage", () => {
  it("traduz AUTH_INVALID_CREDENTIALS", () => {
    expect(
      mapLoginErrorToMessage(new ApiError("AUTH_INVALID_CREDENTIALS", "E-mail ou senha inválidos.")),
    ).toBe("E-mail ou senha inválidos. Verifique e tente novamente.");
  });

  it("traduz AUTH_USER_INACTIVE", () => {
    expect(mapLoginErrorToMessage(new ApiError("AUTH_USER_INACTIVE", "Usuário inativo."))).toBe(
      "Este usuário está inativo. Fale com o administrador do sistema.",
    );
  });

  it("traduz AUTH_RATE_LIMITED", () => {
    expect(mapLoginErrorToMessage(new ApiError("AUTH_RATE_LIMITED", "Tente depois."))).toBe(
      "Muitas tentativas de login. Aguarde e tente novamente.",
    );
  });

  it("orienta o que fazer quando o servidor não responde", () => {
    const message = mapLoginErrorToMessage(
      new ApiError("NETWORK_ERROR", "Não foi possível conectar ao servidor."),
    );

    expect(message).toContain("Verifique sua conexão");
  });

  it("diz QUAL campo está errado quando o backend recusa a validação", () => {
    const message = mapLoginErrorToMessage(
      new ApiError("VALIDATION_ERROR", "Os dados informados são inválidos.", [
        { field: "email", message: "Field required", type: "missing" },
      ]),
    );

    expect(message).toBe("E-mail precisa ser preenchido.");
  });

  it("usa a mensagem do backend para código que ninguém mapeou", () => {
    expect(mapLoginErrorToMessage(new ApiError("AUTH_SOMETHING_NEW", "Texto do backend."))).toBe(
      "Texto do backend.",
    );
  });
});

describe("LoginForm", () => {
  it("desabilita o formulário e mostra 'Entrando…' enquanto envia", async () => {
    let resolveLogin: () => void = () => {};
    const login = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveLogin = resolve;
        }),
    );
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", user: null, login, updateUser: vi.fn(), logout: vi.fn() });

    render(<MemoryRouter><LoginForm /></MemoryRouter>);
    expect(document.querySelector(".login-access-mark .loadx-brand-mark")).toHaveAttribute("src", "/branding/loadx-mark-128.png");

    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "admin@example.test" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-local" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Entrando…")).toBeInTheDocument();
    expect(screen.getByLabelText("E-mail")).toBeDisabled();
    expect(login).toHaveBeenCalledWith("admin@example.test", "senha-local");

    resolveLogin();
  });

  it("mostra a mensagem mapeada quando o login falha", async () => {
    const login = vi
      .fn()
      .mockRejectedValue(new ApiError("AUTH_INVALID_CREDENTIALS", "E-mail ou senha inválidos."));
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", user: null, login, updateUser: vi.fn(), logout: vi.fn() });

    render(<MemoryRouter><LoginForm /></MemoryRouter>);

    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "admin@example.test" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-errada" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "E-mail ou senha inválidos. Verifique e tente novamente.",
    );
  });
});


it("alterna visibilidade sem apagar a senha e preserva recuperação real", () => {
  vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", user: null, login: vi.fn(), updateUser: vi.fn(), logout: vi.fn() });
  render(<MemoryRouter><LoginForm /></MemoryRouter>);
  const password = screen.getByLabelText("Senha");
  fireEvent.change(password, { target: { value: "senha-ficticia" } });
  expect(password).toHaveAttribute("type", "password");
  fireEvent.click(screen.getByRole("button", { name: "Mostrar senha" }));
  expect(password).toHaveAttribute("type", "text");
  expect(password).toHaveValue("senha-ficticia");
  fireEvent.click(screen.getByRole("button", { name: "Ocultar senha" }));
  expect(password).toHaveAttribute("type", "password");
  expect(screen.getByRole("link", { name: "Esqueci minha senha" })).toHaveAttribute("href", "/password-recovery");
});


it("mantém cabeçalho LoadX real separado da arte e botão Entrar acessível", () => {
  vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", user: null, login: vi.fn(), updateUser: vi.fn(), logout: vi.fn() });
  render(<MemoryRouter><LoginForm /></MemoryRouter>);
  expect(screen.getByRole("heading", { name: "Bem-vindo ao LoadX" })).toBeInTheDocument();
  expect(screen.getByText("SMART LOGISTICS")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Entrar" })).toBeEnabled();
});
