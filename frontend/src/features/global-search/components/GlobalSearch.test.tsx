import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "../../auth/hooks/useAuth";
import type { Role } from "../../auth/types";
import { searchRecords, type SearchResult } from "../api/searchApi";
import { GlobalSearch } from "./GlobalSearch";
vi.mock("../api/searchApi");
vi.mock("../../auth/hooks/useAuth");
const RESULTS: SearchResult[] = [
  { category: "order", id: "o1", title: "Pedido o1", href: "/orders?order=o1" },
  { category: "customer", id: "c1", title: "Cliente fictício", href: "/contacts?tab=customers&search=alvo" },
  { category: "truck", id: "t1", title: "ABC1D23 · Baú", href: "/trucks?search=alvo" },
  { category: "driver", id: "d1", title: "Motorista fictício", href: "/contacts?tab=drivers&search=alvo" },
  { category: "trip", id: "v1", title: "Viagem v1", href: "/trips/v1" },
];
function Destination() { const location = useLocation(); return <p>{location.pathname}{location.search}</p>; }
function show(role: Role = "ADMIN", permissions?: string[]) {
  vi.mocked(useAuth).mockReturnValue({ user: { id: "u1", name: "Pessoa", email: "p@example.test", role, permissions, active: true, createdAt: "2026-01-01" } } as ReturnType<typeof useAuth>);
  render(<MemoryRouter><GlobalSearch /><Routes><Route path="*" element={<Destination />} /></Routes></MemoryRouter>);
  const input = screen.getByRole("combobox", { name: "Busca global" });
  fireEvent.focus(input); return input;
}
async function advance(ms = 300) { await act(async () => { vi.advanceTimersByTime(ms); }); }
async function type(input: HTMLElement, text = "alvo") { fireEvent.change(input, { target: { value: text } }); await advance(); }
beforeEach(() => { vi.resetAllMocks(); vi.useFakeTimers(); vi.mocked(searchRecords).mockResolvedValue(RESULTS); });
afterEach(() => { vi.useRealTimers(); });
describe("OC107 busca global", () => {
  it("não consulta vazio/curto e aplica debounce com trim", async () => {
    const input = show(); await advance(); expect(searchRecords).not.toHaveBeenCalled();
    await type(input, "a"); expect(searchRecords).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: " al" } }); await advance(299); expect(searchRecords).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: " alvo " } }); await advance();
    expect(searchRecords).toHaveBeenCalledExactlyOnceWith("alvo", expect.any(AbortSignal));
    expect(screen.getAllByRole("option")).toHaveLength(5);
  });
  it("organiza categorias, seleciona por teclado e fecha o painel", async () => {
    const input = show(); await type(input);
    expect(screen.getByRole("group", { name: "Clientes" })).toHaveTextContent("Cliente fictício");
    fireEvent.keyDown(input, { key: "ArrowDown" }); expect(input).toHaveAttribute("aria-activedescendant", screen.getAllByRole("option")[0].id);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(screen.getByText("/orders?order=o1")).toBeInTheDocument(); expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
  it("seta para cima seleciona o último; Escape preserva foco e não navega", async () => {
    const input = show(); input.focus(); await type(input);
    fireEvent.keyDown(input, { key: "ArrowUp" }); expect(screen.getAllByRole("option").at(-1)).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(input, { key: "Escape" }); expect(input).toHaveFocus(); expect(input).toHaveAttribute("aria-expanded", "false");
    fireEvent.keyDown(input, { key: "Enter" }); expect(screen.queryByText("/trips/v1")).not.toBeInTheDocument();
  });
  it("navega por clique para a listagem filtrada", async () => {
    const input = show(); await type(input); fireEvent.click(screen.getByRole("option", { name: "ABC1D23 · Baú" }));
    expect(screen.getByText("/trucks?search=alvo")).toBeInTheDocument();
  });
  it("distingue carregamento, vazio, falha e nova tentativa", async () => {
    vi.mocked(searchRecords).mockReturnValueOnce(new Promise(() => {}));
    const input = show(); await type(input); expect(screen.getByRole("status")).toHaveTextContent("Buscando");
    vi.mocked(searchRecords).mockRejectedValueOnce(new Error("segredo")); await type(input, "outro");
    expect(screen.getByRole("status")).toHaveTextContent("Não foi possível"); expect(screen.queryByText("segredo")).not.toBeInTheDocument();
    vi.mocked(searchRecords).mockResolvedValueOnce([]); fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" })); await advance();
    expect(screen.getByRole("status")).toHaveTextContent("Nenhum registro");
  });
  it("aborta a consulta anterior e ignora resposta tardia", async () => {
    let resolveOld!: (items: SearchResult[]) => void;
    vi.mocked(searchRecords).mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }));
    const input = show(); await type(input, "velho"); const signal = vi.mocked(searchRecords).mock.calls[0][1];
    vi.mocked(searchRecords).mockResolvedValueOnce([RESULTS[2]]); await type(input, "novo");
    expect(signal.aborted).toBe(true); await act(async () => { resolveOld([RESULTS[1]]); });
    expect(screen.queryByText("Cliente fictício")).not.toBeInTheDocument(); expect(screen.getAllByRole("option")).toHaveLength(1);
  });
  it.each<Role>(["ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER"])("%s apresenta somente categorias permitidas", async (role) => {
    const input = show(role); await type(input); const count = { CUSTOM: 0, ADMIN: 5, LOGISTICS_MANAGER: 5, CHECKER: 2, DRIVER: 1 }[role];
    expect(screen.getAllByRole("option")).toHaveLength(count);
    if (role === "CHECKER" || role === "DRIVER") expect(screen.queryByText("Cliente fictício")).not.toBeInTheDocument();
  });
  it("descarta destinos externos e fecha ao sair do campo", async () => {
    vi.mocked(searchRecords).mockResolvedValue([{ ...RESULTS[0], href: "//external.test" }, { ...RESULTS[2], href: "/\\external.test" }]);
    const input = show(); await type(input); expect(screen.queryByRole("option")).not.toBeInTheDocument();
    fireEvent.blur(input, { relatedTarget: document.body }); expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
  it("limpa a busca por botão acessível e retorna ao início sem nova consulta", async () => {
    const input = show(); await type(input);
    fireEvent.click(screen.getByRole("button", { name: "Limpar busca" }));
    await advance();
    expect(input).toHaveValue(""); expect(input).toHaveFocus();
    expect(screen.getByRole("status")).toHaveTextContent("Digite pelo menos 2 caracteres");
    expect(screen.queryByRole("option")).not.toBeInTheDocument();
    expect(searchRecords).toHaveBeenCalledTimes(1);
  });
  it("apresenta singular e plural naturais no resultado da busca", async () => {
    vi.mocked(searchRecords).mockResolvedValueOnce([RESULTS[0]]);
    const input = show(); await type(input);
    expect(screen.getByRole("status")).toHaveTextContent("1 resultado encontrado.");
    await type(input, "outro");
    expect(screen.getByRole("status")).toHaveTextContent("5 resultados encontrados.");
  });

  it("exibe referência curta e preserva o destino com UUID completo", async () => {
    const id = "12345678-1234-1234-1234-123456789abc";
    vi.mocked(searchRecords).mockResolvedValueOnce([{ ...RESULTS[0], id, title: `Pedido ${id}`, href: `/orders?order=${id}` }]);
    const input = show(); await type(input);
    fireEvent.click(screen.getByRole("option", { name: "Pedido #12345678" }));
    expect(screen.getByText(`/orders?order=${id}`)).toBeInTheDocument();
  });

  it("preserva viagens autorizadas por permissão delegável de um perfil personalizado", async () => {
    const input = show("CUSTOM", ["loadx.trips.read"]); await type(input);
    expect(screen.getAllByRole("option")).toHaveLength(1);
    expect(screen.getByRole("option", { name: "Viagem v1" })).toBeVisible();
    expect(screen.queryByRole("option", { name: "Cliente fictício" })).not.toBeInTheDocument();
  });
  it("mantém a busca vazia para perfil personalizado sem grants", async () => {
    const input = show("CUSTOM", []); await type(input);
    expect(screen.queryByRole("option")).not.toBeInTheDocument();
  });

});
