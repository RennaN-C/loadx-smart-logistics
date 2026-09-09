import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
} from "../api/authApi";
import { useAuth } from "../hooks/useAuth";
import type { AuthenticatedUser } from "../types";
import { AuthProvider } from "./AuthProvider";

vi.mock("../api/authApi", () => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

const USER: AuthenticatedUser = {
  id: "1",
  name: "Ana Souza",
  email: "ana@example.test",
  role: "ADMIN",
  active: true,
  createdAt: "2026-08-01T00:00:00Z",
};

function Probe() {
  const { status, user, login, logout } = useAuth();

  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user?.name ?? ""}</span>
      <button type="button" onClick={() => void login("ana@example.test", "senha-segura") }>
        login
      </button>
      <button type="button" onClick={() => void logout()}>
        logout
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
  });

  it("consulta /auth/me ao montar e resolve cookie ausente como unauthenticated", async () => {
    vi.mocked(getCurrentUser).mockRejectedValue(
      new ApiError("AUTH_INVALID_TOKEN", "Sessão inválida."),
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
    });
    expect(getCurrentUser).toHaveBeenCalledOnce();
    expect(localStorage.length).toBe(0);
  });

  it("restaura o usuário quando o cookie HttpOnly representa sessão válida", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue(USER);

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

  it("usa o usuário devolvido pelo login sem persistir credencial", async () => {
    vi.mocked(getCurrentUser).mockRejectedValue(
      new ApiError("AUTH_INVALID_TOKEN", "Sessão inválida."),
    );
    vi.mocked(loginRequest).mockResolvedValue(USER);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
    });

    fireEvent.click(screen.getByRole("button", { name: "login" }));

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("authenticated");
    });
    expect(localStorage.length).toBe(0);
  });

  it("chama o logout revogável antes de limpar o estado local", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue(USER);
    vi.mocked(logoutRequest).mockResolvedValue();

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("authenticated");
    });

    fireEvent.click(screen.getByRole("button", { name: "logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
    });
    expect(logoutRequest).toHaveBeenCalledOnce();
  });
});
