import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

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

describe("AppLayout", () => {
  it("renderiza o cabeçalho da LoadX e o conteúdo da rota filha", () => {
    vi.mocked(useAuth).mockReturnValue({
      status: "authenticated",
      user: AUTHENTICATED_USER,
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderLayout();

    expect(screen.getByText("LOADX")).toBeInTheDocument();
    expect(screen.getByText("conteudo da rota")).toBeInTheDocument();
  });

  it("mostra o nome do usuário autenticado e permite sair", () => {
    const logout = vi.fn();
    vi.mocked(useAuth).mockReturnValue({
      status: "authenticated",
      user: AUTHENTICATED_USER,
      login: vi.fn(),
      logout,
    });

    renderLayout();

    expect(screen.getByText("Ana Souza")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    expect(logout).toHaveBeenCalledOnce();
  });
});
