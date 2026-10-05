import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { lookupAddressByCep } from "../api/customersApi";
import type { CepAddress } from "../types";
import { CepLookupField } from "./CepLookupField";

vi.mock("../api/customersApi");

/** Endereço fictício: a OC62 responde o `ViaCEPAddress` direto, sem envelope. */
function endereco(overrides: Partial<CepAddress> = {}): CepAddress {
  return {
    cep: "01234567",
    street: "Rua Fictícia",
    neighborhood: "Bairro Fictício",
    complement: null,
    city: "Cidade Fictícia",
    state: "SP",
    ...overrides,
  };
}

function digitar(valor: string) {
  fireEvent.change(screen.getByLabelText("CEP (OPCIONAL)"), { target: { value: valor } });
}

describe("CepLookupField", () => {
  beforeEach(() => {
    vi.mocked(lookupAddressByCep).mockReset();
  });

  it("consulta sozinho quando o CEP fica completo", async () => {
    vi.mocked(lookupAddressByCep).mockResolvedValue(endereco());
    const onFound = vi.fn();

    render(<CepLookupField onFound={onFound} />);
    digitar("01234567");

    await waitFor(() => expect(onFound).toHaveBeenCalledWith(endereco()));
    expect(lookupAddressByCep).toHaveBeenCalledWith("01234567");
  });

  it("não consulta com CEP pela metade", () => {
    render(<CepLookupField onFound={vi.fn()} />);
    digitar("0123");

    expect(lookupAddressByCep).not.toHaveBeenCalled();
  });

  it("não repete a consulta a cada tecla depois de completo", async () => {
    vi.mocked(lookupAddressByCep).mockResolvedValue(endereco());

    render(<CepLookupField onFound={vi.fn()} />);
    digitar("01234567");
    await waitFor(() => expect(lookupAddressByCep).toHaveBeenCalledOnce());

    // Dígito a mais é descartado pela máscara, mas ainda dispara onChange. Sem a
    // guarda, cada tecla extra viraria uma consulta.
    digitar("012345678");
    digitar("01234-567");

    expect(lookupAddressByCep).toHaveBeenCalledOnce();
  });

  it("aplica a máscara enquanto se digita", () => {
    render(<CepLookupField onFound={vi.fn()} />);
    digitar("01234567");

    expect(screen.getByLabelText("CEP (OPCIONAL)")).toHaveValue("01234-567");
  });

  it("mostra bairro e complemento como dica, que é onde cabem", async () => {
    vi.mocked(lookupAddressByCep).mockResolvedValue(
      endereco({ neighborhood: "Centro", complement: "lado ímpar" }),
    );

    render(<CepLookupField onFound={vi.fn()} />);
    digitar("01234567");

    // `Customer` não tem coluna para os dois; virar texto no endereço composto
    // exigiria um formato que ninguém aprovou.
    expect(await screen.findByText("Bairro: Centro · Complemento: lado ímpar")).toBeInTheDocument();
  });

  it("não inventa dica quando o CEP é municipal e não tem bairro", async () => {
    vi.mocked(lookupAddressByCep).mockResolvedValue(
      endereco({ street: null, neighborhood: null, complement: null }),
    );
    const onFound = vi.fn();

    render(<CepLookupField onFound={onFound} />);
    digitar("01234567");

    await waitFor(() => expect(onFound).toHaveBeenCalled());
    expect(screen.queryByText(/Bairro:/)).not.toBeInTheDocument();
  });

  it("avisa a falha no próprio campo e não chama onFound", async () => {
    vi.mocked(lookupAddressByCep).mockRejectedValue(
      new ApiError("VIACEP_NOT_FOUND", "CEP não encontrado."),
    );
    const onFound = vi.fn();

    render(<CepLookupField onFound={onFound} />);
    digitar("01234567");

    const campo = screen.getByLabelText("CEP (OPCIONAL)");
    await waitFor(() => expect(campo).toHaveAccessibleDescription(/CEP não encontrado/));
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(onFound).not.toHaveBeenCalled();
  });

  it("toda falha diz que dá para preencher à mão", async () => {
    const casos = [
      ["VIACEP_UNAVAILABLE", /fora do ar/],
      ["VIACEP_TIMEOUT", /demorou demais/],
      ["VIACEP_INVALID_RESPONSE", /inesperado/],
    ] as const;

    for (const [codigo, trecho] of casos) {
      vi.mocked(lookupAddressByCep).mockRejectedValue(new ApiError(codigo, "x"));
      const { unmount } = render(<CepLookupField onFound={vi.fn()} />);
      digitar("01234567");

      const campo = screen.getByLabelText("CEP (OPCIONAL)");
      await waitFor(() => expect(campo).toHaveAccessibleDescription(trecho));
      expect(campo).toHaveAccessibleDescription(/à mão/);
      unmount();
    }
  });

  it("o botão refaz a consulta depois de uma falha", async () => {
    vi.mocked(lookupAddressByCep).mockRejectedValueOnce(new ApiError("VIACEP_TIMEOUT", "x"));
    const onFound = vi.fn();

    render(<CepLookupField onFound={onFound} />);
    digitar("01234567");
    await waitFor(() =>
      expect(screen.getByLabelText("CEP (OPCIONAL)")).toHaveAttribute("aria-invalid", "true"),
    );

    vi.mocked(lookupAddressByCep).mockResolvedValue(endereco());
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));

    await waitFor(() => expect(onFound).toHaveBeenCalled());
    expect(screen.getByLabelText("CEP (OPCIONAL)")).not.toHaveAttribute("aria-invalid");
  });

  it("o botão fica travado sem CEP completo e enquanto a consulta corre", async () => {
    // A promessa é liberada à mão: com um mock que resolve na hora, o estado de
    // carregamento dura menos que a asserção e o teste fica intermitente.
    let liberar: (() => void) | undefined;
    vi.mocked(lookupAddressByCep).mockImplementation(
      () =>
        new Promise<CepAddress>((resolve) => {
          liberar = () => resolve(endereco());
        }),
    );

    render(<CepLookupField onFound={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();

    digitar("0123");
    expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();

    // Completar o CEP já dispara a consulta: o botão vira "Buscando…".
    digitar("01234567");
    await waitFor(() => expect(screen.getByRole("button", { name: "Buscando…" })).toBeDisabled());

    liberar?.();
    await waitFor(() => expect(screen.getByRole("button", { name: "Buscar" })).toBeEnabled());
  });

  it("Enter tenta de novo em vez de enviar o formulário", async () => {
    vi.mocked(lookupAddressByCep).mockRejectedValue(new ApiError("VIACEP_TIMEOUT", "x"));
    const onSubmit = vi.fn((e: React.FormEvent) => e.preventDefault());

    render(
      <form onSubmit={onSubmit}>
        <CepLookupField onFound={vi.fn()} />
      </form>,
    );
    digitar("01234567");
    await waitFor(() => expect(lookupAddressByCep).toHaveBeenCalledOnce());

    fireEvent.keyDown(screen.getByLabelText("CEP (OPCIONAL)"), { key: "Enter" });

    await waitFor(() => expect(lookupAddressByCep).toHaveBeenCalledTimes(2));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("resposta atrasada de um CEP antigo não sobrescreve a nova", async () => {
    // Trocar o CEP rápido dispara duas consultas, e nada garante a ordem de
    // volta. Sem a guarda, a primeira resposta chegaria por último e venceria.
    const primeiro = endereco({ city: "Cidade Antiga" });
    const segundo = endereco({ city: "Cidade Nova" });
    let liberarPrimeira: (() => void) | undefined;

    vi.mocked(lookupAddressByCep)
      .mockImplementationOnce(
        () =>
          new Promise<CepAddress>((resolve) => {
            liberarPrimeira = () => resolve(primeiro);
          }),
      )
      .mockResolvedValueOnce(segundo);

    const onFound = vi.fn();
    render(<CepLookupField onFound={onFound} />);

    digitar("01234567");
    digitar("09876543");
    await waitFor(() => expect(onFound).toHaveBeenCalledWith(segundo));

    liberarPrimeira?.();
    await waitFor(() => expect(lookupAddressByCep).toHaveBeenCalledTimes(2));

    expect(onFound).toHaveBeenCalledOnce();
    expect(onFound).not.toHaveBeenCalledWith(primeiro);
  });
});
