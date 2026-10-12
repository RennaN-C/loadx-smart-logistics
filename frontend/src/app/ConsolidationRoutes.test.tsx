import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { getCurrentUser } from "../features/auth/api/authApi";
import type { Role } from "../features/auth/types";
import { useAuth } from "../features/auth/hooks/useAuth";
const pages = vi.hoisted(() => ({ dashboard: vi.fn(), trucks: vi.fn(), reports: vi.fn() }));
vi.mock("../features/auth/api/authApi");
vi.mock("../features/dashboard/pages/DashboardPage", () => ({ DashboardPage: () => { pages.dashboard(); const { user } = useAuth(); return <h1>Visão geral {user?.role}</h1>; } }));
vi.mock("../features/trucks/pages/TruckWorkspacePage", () => ({ TruckWorkspacePage: () => { pages.trucks(); return <h1>Caminhões e frota</h1>; } }));
vi.mock("../features/reports/pages/ReportsPage", () => ({ ReportsPage: () => { pages.reports(); return <h1>Relatórios e indicadores</h1>; } }));
const ROLES: readonly Role[] = ["ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER"];
beforeEach(() => vi.clearAllMocks());
function open(role: Role, path: string) {
  window.history.replaceState({}, "", path);
  vi.mocked(getCurrentUser).mockResolvedValue({ id: "user", name: "Conta de teste", email: "account@example.test", role, active: true, createdAt: "2026-01-01T00:00:00Z" });
  return render(<App />);
}
describe("Consolidação e compatibilidade de rotas", () => {
  it.each(ROLES)("%s mantém entrada contextual na raiz", async (role) => {
    open(role, "/"); await screen.findByRole("heading", { name: `Visão geral ${role}` });
  });
  it.each(["ADMIN", "LOGISTICS_MANAGER"] as const)("%s abre /operations na visão geral", async (role) => {
    open(role, "/operations");
    await screen.findByRole("heading", { name: `Visão geral ${role}` });
    expect(window.location.pathname).toBe("/");
  });
  it.each(["CHECKER", "DRIVER"] as const)("%s não monta indicadores pelo alias /operations", async (role) => {
    open(role, "/operations");
    await screen.findByRole("heading", { name: "Acesso negado" });
    expect(pages.dashboard).not.toHaveBeenCalled();
  });
  it.each(["ADMIN", "LOGISTICS_MANAGER", "CHECKER"] as const)("%s usa /fleet como atalho de disponibilidade", async (role) => {
    open(role, "/fleet");
    await screen.findByRole("heading", { name: "Caminhões e frota" });
    await waitFor(() => expect(window.location.pathname + window.location.search).toBe("/trucks?tab=availability"));
  });
  it.each(["/fleet", "/trucks", "/reports"])("DRIVER não monta consultas protegidas em %s", async (path) => {
    open("DRIVER", path);
    await screen.findByRole("heading", { name: "Acesso negado" });
    expect(pages.trucks).not.toHaveBeenCalled();
    expect(pages.reports).not.toHaveBeenCalled();
  });
});
