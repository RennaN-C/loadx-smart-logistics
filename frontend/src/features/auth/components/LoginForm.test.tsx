import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useAuth } from "../hooks/useAuth";
import { LoginForm } from "./LoginForm";
import { mapLoginErrorToMessage } from "./loginErrorMessages";

vi.mock("../hooks/useAuth");

describe("mapLoginErrorToMessage", () => {
  it("traduz AUTH_INVALID_CREDENTIALS", () => {
    expect(
      mapLoginErrorToMessage({
        code: "AUTH_INVALID_CREDENTIALS",
        message: "E-mail ou senha inválidos.",
        details: [],
      }),
    ).toBe("E-mail ou senha inválidos. Verifique e tente novamente.");
  });

  it("traduz AUTH_USER_INACTIVE", () => {
    expect(
      mapLoginErrorToMessage({ code: "AUTH_USER_INACTIVE", message: "Usuário inativo.", details: [] }),
    ).toBe("Este usuário está inativo. Fale com o administrador do sistema.");
  });

  it("usa a mensagem do backend para qualquer outro código", () => {
    expect(
      mapLoginErrorToMessage({
        code: "NETWORK_ERROR",
        message: "Não foi possível conectar ao servidor.",
        details: [],
      }),
    ).toBe("Não foi possível conectar ao servidor.");
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
    const login = vi.fn().mockRejectedValue({
      code: "AUTH_INVALID_CREDENTIALS",
      message: "E-mail ou senha inválidos.",
      details: [],
    });
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
