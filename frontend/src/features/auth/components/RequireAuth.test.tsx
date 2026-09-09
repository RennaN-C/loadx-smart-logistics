import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { useAuth } from "../hooks/useAuth";
import { RequireAuth } from "./RequireAuth";

vi.mock("../hooks/useAuth");

function renderWithRoute() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/login" element={<p>tela de login</p>} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<p>conteudo protegido</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("RequireAuth", () => {
  it("redireciona para /login quando não autenticado", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "unauthenticated",
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderWithRoute();

    expect(screen.getByText("tela de login")).toBeInTheDocument();
    expect(screen.queryByText("conteudo protegido")).not.toBeInTheDocument();
  });

  it("renderiza o conteúdo protegido quando autenticado", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "authenticated",
      user: {
        id: "1",
        name: "Ana Souza",
        email: "ana@example.test",
        role: "ADMIN",
        active: true,
        createdAt: "2026-08-01T00:00:00Z",
      },
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderWithRoute();

    expect(screen.getByText("conteudo protegido")).toBeInTheDocument();
  });

  it("mostra o estado de carregamento enquanto a sessão é restaurada", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "loading",
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderWithRoute();

    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
