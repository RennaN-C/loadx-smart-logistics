import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ScanField, type ScanOutcome } from "./ScanField";

const CODE = "loadx:loading-item:11111111-1111-4111-8111-111111111111";

describe("ScanField — leitor e recuperação", () => {
  it("não duplica leituras simultâneas e recupera o foco após a resposta", async () => {
    let finish!: (value: ScanOutcome) => void;
    const onScan = vi.fn(() => new Promise<ScanOutcome>((resolve) => { finish = resolve; }));
    render(<ScanField disabled={false} onScan={onScan} />);
    const input = screen.getByRole<HTMLInputElement>("textbox", { name: "LER CÓDIGO DO VOLUME" });
    fireEvent.change(input, { target: { value: CODE } });
    const form = input.closest("form") as HTMLFormElement;
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(onScan).toHaveBeenCalledTimes(1);
    await act(async () => { finish({ ok: true, message: "Volume conferido." }); });
    expect(screen.getByRole("status")).toHaveTextContent("Volume conferido.");
    await waitFor(() => expect(input).toHaveFocus());
    expect(input.value).toBe("");
  });

  it("mostra erro recuperável se a operação lançar uma exceção", async () => {
    const onScan = vi.fn().mockRejectedValueOnce(new Error("network unavailable"));
    render(<ScanField disabled={false} onScan={onScan} />);
    const input = screen.getByRole<HTMLInputElement>("textbox", { name: "LER CÓDIGO DO VOLUME" });
    fireEvent.change(input, { target: { value: CODE } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);
    expect(await screen.findByRole("status")).toHaveTextContent("Não foi possível conferir o código.");
    await waitFor(() => expect(input).toHaveFocus());
    expect(input).toBeEnabled();
  });

  it("não executa leitura se a conferência estiver bloqueada", () => {
    const onScan = vi.fn();
    render(<ScanField disabled disabledReason="Inicie a conferência." onScan={onScan} />);
    expect(screen.getByRole("textbox", { name: "LER CÓDIGO DO VOLUME" })).toBeDisabled();
    expect(screen.getByText("Inicie a conferência.")).toBeInTheDocument();
    expect(onScan).not.toHaveBeenCalled();
  });
});
