import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppearancePreferences } from "../../features/auth/components/AppearancePreferences";
import { useDarkAppearance } from "./useAppearance";

let dark = false;
let change: () => void;
async function boot(saved?: string) {
  if (saved) localStorage.setItem("loadx.appearance", saved);
  vi.stubGlobal("matchMedia", () => ({ get matches() { return dark; }, addEventListener: (_: string, listener: () => void) => { change = listener; } }));
  vi.resetModules();
  await import("../../../public/theme.js");
}
function SceneTheme() { return <output>{useDarkAppearance() ? "Cena escura" : "Cena clara"}</output>; }
beforeEach(() => { localStorage.clear(); dark = false; });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); act(() => window.loadxTheme.set("system")); });
describe("preferência global de aparência", () => {
  it("começa em automático e acompanha o sistema e a cena 3D", async () => {
    await boot(); render(<><AppearancePreferences /><SceneTheme /></>);
    expect(screen.getByRole("radio", { name: /Automático/ })).toBeChecked();
    expect(document.documentElement.dataset.theme).toBe("light");
    act(() => { dark = true; change(); });
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(screen.getByText("Cena escura")).toBeInTheDocument();
    act(() => { dark = false; change(); });
    expect(screen.getByText("Cena clara")).toBeInTheDocument();
  });
  it.each([["light", true, "Claro"], ["dark", false, "Escuro"]] as const)("restaura %s independentemente do sistema", async (saved, system, label) => {
    dark = system; await boot(saved); render(<AppearancePreferences />);
    expect(screen.getByRole("radio", { name: new RegExp(label) })).toBeChecked();
    expect(document.documentElement.dataset.theme).toBe(saved);
    act(() => change()); expect(document.documentElement.dataset.theme).toBe(saved);
  });
  it("aplica imediatamente e persiste após reinicialização", async () => {
    await boot(); render(<><AppearancePreferences /><SceneTheme /></>);
    fireEvent.click(screen.getByRole("radio", { name: /Escuro/ }));
    expect(screen.getByText("Cena escura")).toBeInTheDocument();
    expect(localStorage.getItem("loadx.appearance")).toBe("dark");
    await boot(); expect(document.documentElement.dataset.theme).toBe("dark");
  });
  it("mantém escolha em memória com armazenamento bloqueado", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    await boot(); render(<AppearancePreferences />);
    fireEvent.click(screen.getByRole("radio", { name: /Escuro/ }));
    expect(screen.getByRole("radio", { name: /Escuro/ })).toBeChecked();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
  it("ignora valores inválidos e sincroniza outra aba ou limpeza", async () => {
    await boot("invalid"); expect(window.loadxTheme.preference()).toBe("system");
    window.dispatchEvent(new StorageEvent("storage", { key: "loadx.appearance", newValue: "dark" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    window.dispatchEvent(new StorageEvent("storage", { key: null }));
    expect(window.loadxTheme.preference()).toBe("system");
    window.loadxTheme.set("invalid" as "light"); expect(window.loadxTheme.preference()).toBe("system");
  });
});
