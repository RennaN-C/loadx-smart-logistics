import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearToken, getToken, setToken } from "../../../services/tokenStorage";
import { getCurrentUser } from "../api/authApi";
import { useAuth } from "../hooks/useAuth";
import { AuthProvider } from "./AuthProvider";

vi.mock("../api/authApi", () => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
}));

function Probe() {
  const { status, user } = useAuth();

  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user?.name ?? ""}</span>
    </div>
  );
}

describe("AuthProvider", () => {
  afterEach(() => {
    clearToken();
    vi.resetAllMocks();
  });

  it("sem token salvo, resolve direto para unauthenticated sem chamar getCurrentUser", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
    });
    expect(getCurrentUser).not.toHaveBeenCalled();
  });

  it("com token salvo e sessão válida, restaura o usuário autenticado", async () => {
    setToken("token-valido");
    vi.mocked(getCurrentUser).mockResolvedValue({
      id: "1",
      name: "Ana Souza",
      email: "ana@example.test",
      role: "ADMIN",
      active: true,
      createdAt: "2026-08-01T00:00:00Z",
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("authenticated");
    });
    expect(screen.getByTestId("user").textContent).toBe("Ana Souza");
  });

  it("com token salvo mas sessão inválida, limpa o token e cai para unauthenticated", async () => {
    setToken("token-expirado");
    vi.mocked(getCurrentUser).mockRejectedValue({
      code: "AUTH_INVALID_TOKEN",
      message: "Token inválido.",
      details: [],
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
    });
    expect(getToken()).toBeNull();
  });
});
