import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReportTableViewport } from "./ReportTableViewport";

describe("Rolagem acessível de relatórios", () => {
  it("não oferece controles quando todas as colunas cabem", () => {
    render(<ReportTableViewport label="Tabela de teste"><table><tbody><tr><td>Conteúdo</td></tr></tbody></table></ReportTableViewport>);
    expect(screen.getByRole("region", { name: "Tabela de teste" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
  it("controles nativos movem as colunas e respeitam os limites", () => {
    render(<ReportTableViewport label="Tabela de teste"><table><tbody><tr><td>Conteúdo</td></tr></tbody></table></ReportTableViewport>);
    const viewport = screen.getByRole("region", { name: "Tabela de teste" });
    Object.defineProperties(viewport, { clientWidth: { value: 300 }, scrollWidth: { value: 600 }, scrollLeft: { value: 0, writable: true } });
    const scrollBy = vi.fn(({ left }: { left: number }) => { viewport.scrollLeft = Math.max(0, Math.min(300, viewport.scrollLeft + left)); fireEvent.scroll(viewport); });
    Object.defineProperty(viewport, "scrollBy", { value: scrollBy });
    fireEvent(window, new Event("resize"));
    const previous = screen.getByRole("button", { name: "Colunas anteriores" });
    const next = screen.getByRole("button", { name: "Próximas colunas" });
    expect(previous).toBeDisabled();
    fireEvent.click(next);
    expect(scrollBy).toHaveBeenLastCalledWith({ left: 240, behavior: "auto" });
    expect(previous).toBeEnabled();
    fireEvent.click(next);
    expect(next).toBeDisabled();
    fireEvent.click(previous);
    expect(viewport.scrollLeft).toBe(60);
  });
});
