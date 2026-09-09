import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../../services/api";
import { ApiError } from "../../../types/api";
import { downloadLoadingReport, downloadTripReport, saveBlob } from "./reportsApi";

vi.mock("../../../services/api", () => ({ api: { get: vi.fn() } }));

/**
 * Resposta de erro do backend, entregue como Blob por causa do `responseType`.
 *
 * O `Blob` do jsdom não implementa `text()` nem `arrayBuffer()` — só o
 * `FileReader` lê ali. Em vez de remendar `Blob.prototype` globalmente, o
 * próprio teste entrega o método que falta nesta instância: continua sendo um
 * `Blob` de verdade, então o `instanceof` do código de produção segue valendo,
 * e nenhum `FileReader` entra no projeto.
 */
function erroComoBlob(status: number, code: string, message: string) {
  const corpo = JSON.stringify({ code, message, details: [] });
  const data = comText(new Blob([corpo], { type: "application/json" }), corpo);

  return { status, data };
}

function comText(blob: Blob, conteudo: string): Blob {
  Object.defineProperty(blob, "text", { value: () => Promise.resolve(conteudo) });
  return blob;
}

describe("reportsApi", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset();
  });

  it("pede o PDF sem deixar o interceptor global engolir o erro", async () => {
    const pdf = new Blob(["%PDF"], { type: "application/pdf" });
    vi.mocked(api.get).mockResolvedValue({ status: 200, data: pdf });

    await expect(downloadLoadingReport("lp1")).resolves.toBe(pdf);

    const [caminho, config] = vi.mocked(api.get).mock.calls[0];
    expect(caminho).toBe("/reports/load-plans/lp1");
    expect(config).toMatchObject({ responseType: "blob" });
    // validateStatus precisa aceitar tudo, senão o corpo do erro se perde
    expect((config as { validateStatus: (s: number) => boolean }).validateStatus(404)).toBe(true);
  });

  it("lê o código de dentro do Blob de erro, em vez de virar erro genérico", async () => {
    vi.mocked(api.get).mockResolvedValue(
      erroComoBlob(404, "LOADING_SESSION_NOT_FOUND", "Carregamento não encontrado."),
    );

    await expect(downloadLoadingReport("lp1")).rejects.toMatchObject({
      code: "LOADING_SESSION_NOT_FOUND",
    });
  });

  it("preserva a MENSAGEM do backend, não só o código deduzido do status", async () => {
    // 403 cairia em AUTH_FORBIDDEN mesmo sem ler o corpo; a mensagem é o que
    // prova que o Blob foi realmente lido.
    vi.mocked(api.get).mockResolvedValue(erroComoBlob(403, "AUTH_FORBIDDEN", "Acesso negado."));

    await expect(downloadTripReport("t1")).rejects.toMatchObject({
      code: "AUTH_FORBIDDEN",
      message: "Acesso negado.",
    });
  });

  it("não quebra quando o corpo do erro não é JSON", async () => {
    vi.mocked(api.get).mockResolvedValue({
      status: 500,
      data: comText(new Blob(["<html>erro</html>"], { type: "text/html" }), "<html>erro</html>"),
    });

    const erro = await downloadTripReport("t1").catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ApiError);
    expect((erro as ApiError).code).toBe("UNKNOWN_ERROR");
  });

  it("monta o caminho da viagem", async () => {
    vi.mocked(api.get).mockResolvedValue({ status: 200, data: new Blob(["%PDF"]) });

    await downloadTripReport("t9");

    expect(vi.mocked(api.get).mock.calls[0][0]).toBe("/reports/trips/t9");
  });
});

describe("saveBlob", () => {
  it("entrega o arquivo e limpa o link, sem deixar lixo no documento", () => {
    const criar = vi.fn(() => "blob:url");
    const revogar = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: criar, revokeObjectURL: revogar });
    const clique = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    saveBlob(new Blob(["%PDF"]), "relatorio.pdf");

    expect(criar).toHaveBeenCalledOnce();
    expect(clique).toHaveBeenCalledOnce();
    expect(document.querySelector("a[download]")).toBeNull();

    clique.mockRestore();
    vi.unstubAllGlobals();
  });
});
