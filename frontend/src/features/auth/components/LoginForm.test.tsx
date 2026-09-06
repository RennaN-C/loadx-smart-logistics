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
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", user: null, login, logout: vi.fn() });

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("E-MAIL"), { target: { value: "admin@example.test" } });
    fireEvent.change(screen.getByLabelText("SENHA"), { target: { value: "senha-local" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Entrando…")).toBeInTheDocument();
    expect(screen.getByLabelText("E-MAIL")).toBeDisabled();
    expect(login).toHaveBeenCalledWith("admin@example.test", "senha-local");

    resolveLogin();
  });

  it("mostra a mensagem mapeada quando o login falha", async () => {
    const login = vi
      .fn()
      .mockRejectedValue(new ApiError("AUTH_INVALID_CREDENTIALS", "E-mail ou senha inválidos."));
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", user: null, login, logout: vi.fn() });

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("E-MAIL"), { target: { value: "admin@example.test" } });
    fireEvent.change(screen.getByLabelText("SENHA"), { target: { value: "senha-errada" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "E-mail ou senha inválidos. Verifique e tente novamente.",
    );
  });
});
