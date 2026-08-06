import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearToken, getToken, setToken } from "../../../services/tokenStorage";
import { ApiError } from "../../../types/api";
import { getCurrentUser } from "../api/authApi";
import { useAuth } from "../hooks/useAuth";
import { AuthProvider } from "./AuthProvider";

vi.mock("../api/authApi", () => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
}));

function base64Url(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function makeJwt(): string {
  const header = base64Url({ alg: "HS256", typ: "JWT" });
  const payload = base64Url({ sub: "user-1", exp: Math.floor(Date.now() / 1000) + 3600 });
  return `${header}.${payload}.fake-signature`;
}

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
    setToken(makeJwt());
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
    setToken(makeJwt());
    vi.mocked(getCurrentUser).mockRejectedValue(new ApiError("AUTH_INVALID_TOKEN", "Token inválido."));

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
