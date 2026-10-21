import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MfaProvisioning } from "./MfaProvisioning";

const uri = "otpauth://totp/LoadX:test?secret=JBSWY3DPEHPK3PXP&issuer=LoadX";
describe("provisionamento local", () => {
  it("renderiza QR vetorial local com alternativa manual e sem recursos remotos", () => {
    const { container, rerender } = render(<MfaProvisioning uri={uri} />);
    expect(screen.getByTitle("QR Code para configurar o autenticador LoadX")).toBeInTheDocument();
    expect(container.querySelector("svg path")).toBeInTheDocument();
    expect(container.querySelector("img,iframe,canvas")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Chave de configuração")).toHaveValue("JBSWY3DPEHPK3PXP");
    rerender(<MfaProvisioning uri={uri} />);
    expect(screen.getByLabelText("URI de provisionamento")).toHaveValue(uri);
  });
  it("copia a chave e oferece alternativa quando clipboard falha", async () => {
    const writeText = vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValueOnce(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    render(<MfaProvisioning uri={uri} />);
    fireEvent.click(screen.getByText("Não consegue escanear? Use a chave manual"));
    fireEvent.click(screen.getByRole("button", { name: "Copiar chave" }));
    await screen.findByText(/Não foi possível copiar/);
    fireEvent.click(screen.getByRole("button", { name: "Copiar chave" }));
    await screen.findByText(/Chave copiada/);
    expect(writeText).toHaveBeenLastCalledWith("JBSWY3DPEHPK3PXP");
  });
});
