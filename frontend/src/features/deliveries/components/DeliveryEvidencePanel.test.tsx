import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import {
  downloadDeliveryEvidence,
  getDeliveryReceipt,
  listDeliveryEvidences,
  registerDeliveryEvidence,
  revokeDeliveryEvidence,
} from "../api/evidencesApi";
import type { DeliveryEvidence, DeliveryReceipt } from "../types";
import { DeliveryEvidencePanel } from "./DeliveryEvidencePanel";

vi.mock("../api/evidencesApi");

function receipt(): DeliveryReceipt {
  return {
    id: "r1",
    deliveryId: "d1",
    tripId: "t1",
    orderId: "o1",
    driverId: "dr1",
    deliveredAt: "2026-10-10T18:00:00Z",
    recordedAt: "2026-10-10T18:05:00Z",
    recordedBy: "u1",
  };
}

function evidence(overrides: Partial<DeliveryEvidence> = {}): DeliveryEvidence {
  return {
    id: "e1",
    deliveryId: "d1",
    receiptId: "r1",
    kind: "PHOTO",
    mediaType: "image/png",
    sizeBytes: 2048,
    sha256: "abc",
    status: "ACTIVE",
    recordedBy: "u1",
    recordedAt: "2026-10-10T18:06:00Z",
    revokedBy: null,
    revokedAt: null,
    ...overrides,
  };
}

function page(items: DeliveryEvidence[]) {
  return { items, page: 1, pageSize: 100, total: items.length, totalPages: 1 };
}

function escolherArquivo(nome = "foto.png") {
  const file = new File(["pixels"], nome, { type: "image/png" });
  fireEvent.change(screen.getByLabelText("IMAGEM"), { target: { files: [file] } });
}

beforeEach(() => {
  vi.mocked(getDeliveryReceipt).mockReset().mockResolvedValue(receipt());
  vi.mocked(listDeliveryEvidences).mockReset().mockResolvedValue(page([]));
  vi.mocked(registerDeliveryEvidence).mockReset().mockResolvedValue(evidence());
  vi.mocked(revokeDeliveryEvidence).mockReset().mockResolvedValue(evidence({ status: "REVOKED" }));
  vi.mocked(downloadDeliveryEvidence).mockReset();
});

describe("DeliveryEvidencePanel — comprovante", () => {
  it("mostra os dois horários do comprovante, que são distintos", async () => {
    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);

    expect(await screen.findByText("ENTREGUE EM")).toBeInTheDocument();
    expect(screen.getByText("REGISTRADO EM")).toBeInTheDocument();
  });

  it("entrega não concluída explica a ordem das coisas, e não pede evidências", async () => {
    vi.mocked(getDeliveryReceipt).mockRejectedValue(
      new ApiError("DELIVERY_RECEIPT_NOT_AVAILABLE", "indisponível", [], 409),
    );

    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/ainda não foi concluída/);
    // sem comprovante não faz sentido pedir a lista: responderia o mesmo erro
    expect(listDeliveryEvidences).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("IMAGEM")).not.toBeInTheDocument();
  });

  it("oferece nova tentativa quando a carga falha", async () => {
    vi.mocked(getDeliveryReceipt).mockRejectedValueOnce(
      new ApiError("NETWORK_ERROR", "sem rede"),
    );

    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));

    expect(await screen.findByText("ENTREGUE EM")).toBeInTheDocument();
  });
});

describe("DeliveryEvidencePanel — permissões", () => {
  it("quem só consulta não recebe formulário nem revogar", async () => {
    vi.mocked(listDeliveryEvidences).mockResolvedValue(page([evidence()]));

    render(<DeliveryEvidencePanel deliveryId="d1" canOperate={false} />);

    await screen.findByText("Foto");
    expect(screen.queryByLabelText("IMAGEM")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revogar" })).not.toBeInTheDocument();
    // baixar continua, que é leitura
    expect(screen.getByRole("button", { name: "Baixar" })).toBeInTheDocument();
  });

  it("403 do backend vira frase sobre perfil", async () => {
    vi.mocked(getDeliveryReceipt).mockRejectedValue(
      new ApiError("AUTH_FORBIDDEN", "negado", [], 403),
    );

    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/Seu perfil não registra/);
  });
});

describe("DeliveryEvidencePanel — registro", () => {
  it("envia tipo e conteúdo em base64", async () => {
    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);
    await screen.findByText("ENTREGUE EM");

    fireEvent.change(screen.getByLabelText("TIPO"), { target: { value: "SIGNATURE" } });
    escolherArquivo();
    fireEvent.click(screen.getByRole("button", { name: "Registrar evidência" }));

    await waitFor(() => expect(registerDeliveryEvidence).toHaveBeenCalled());
    const [deliveryId, input] = vi.mocked(registerDeliveryEvidence).mock.calls[0];
    expect(deliveryId).toBe("d1");
    expect(input.kind).toBe("SIGNATURE");
    expect(input.contentBase64).toBe(btoa("pixels"));
    expect(input.eventId).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("o REENVIO usa a MESMA chave: falha de rede não vira evidência duplicada", async () => {
    // O backend tem UNIQUE (recorded_by, event_id) e devolve o registro
    // original. Gerar chave nova a cada tentativa jogaria essa proteção fora.
    vi.mocked(registerDeliveryEvidence)
      .mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "sem rede"))
      .mockResolvedValue(evidence());

    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);
    await screen.findByText("ENTREGUE EM");
    escolherArquivo();
    fireEvent.click(screen.getByRole("button", { name: "Registrar evidência" }));

    const retry = await screen.findByRole("button", { name: "Tentar novamente" });
    fireEvent.click(retry);

    await waitFor(() => expect(registerDeliveryEvidence).toHaveBeenCalledTimes(2));
    const primeira = vi.mocked(registerDeliveryEvidence).mock.calls[0][1].eventId;
    const segunda = vi.mocked(registerDeliveryEvidence).mock.calls[1][1].eventId;
    expect(segunda).toBe(primeira);
  });

  it("arquivo NOVO ganha chave nova: reaproveitar daria conflito de identidade", async () => {
    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);
    await screen.findByText("ENTREGUE EM");

    escolherArquivo("primeira.png");
    fireEvent.click(screen.getByRole("button", { name: "Registrar evidência" }));
    await waitFor(() => expect(registerDeliveryEvidence).toHaveBeenCalledTimes(1));

    escolherArquivo("segunda.png");
    fireEvent.click(screen.getByRole("button", { name: "Registrar evidência" }));
    await waitFor(() => expect(registerDeliveryEvidence).toHaveBeenCalledTimes(2));

    const calls = vi.mocked(registerDeliveryEvidence).mock.calls;
    expect(calls[1][1].eventId).not.toBe(calls[0][1].eventId);
  });

  it("recusa arquivo fora do contrato antes de enviar", async () => {
    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);
    await screen.findByText("ENTREGUE EM");

    const pdf = new File(["x"], "nota.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("IMAGEM"), { target: { files: [pdf] } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar evidência" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/PNG\/JPEG/);
    expect(registerDeliveryEvidence).not.toHaveBeenCalled();
  });

  it("armazenamento fora do ar diz que NADA foi registrado", async () => {
    vi.mocked(registerDeliveryEvidence).mockRejectedValue(
      new ApiError("EVIDENCE_STORAGE_UNAVAILABLE", "indisponível", [], 503),
    );

    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);
    await screen.findByText("ENTREGUE EM");
    escolherArquivo();
    fireEvent.click(screen.getByRole("button", { name: "Registrar evidência" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Nada foi registrado/);
  });
});

describe("DeliveryEvidencePanel — lista", () => {
  it("explica a ausência em vez de mostrar lista vazia", async () => {
    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);

    expect(await screen.findByText(/Nenhuma evidência registrada/)).toBeInTheDocument();
  });

  it("distingue ativa de revogada, e revogada não baixa", async () => {
    vi.mocked(listDeliveryEvidences).mockResolvedValue(
      page([
        evidence(),
        evidence({
          id: "e2",
          kind: "SIGNATURE",
          status: "REVOKED",
          revokedAt: "2026-10-11T09:00:00Z",
          revokedBy: "u2",
        }),
      ]),
    );

    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);

    // Escopado na LISTA: "Assinatura" também é opção do seletor de tipo.
    const lista = (await screen.findByRole("list")) as HTMLElement;
    const revogada = within(lista).getByText("Assinatura").closest("li") as HTMLElement;
    expect(within(revogada).getByText("Revogada")).toBeInTheDocument();
    expect(within(revogada).queryByRole("button", { name: "Baixar" })).not.toBeInTheDocument();
  });

  it("revogar pede confirmação: o contrato não prevê reativação", async () => {
    vi.mocked(listDeliveryEvidences).mockResolvedValue(page([evidence()]));
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<DeliveryEvidencePanel deliveryId="d1" canOperate />);
    fireEvent.click(await screen.findByRole("button", { name: "Revogar" }));

    expect(confirm).toHaveBeenCalled();
    expect(revokeDeliveryEvidence).not.toHaveBeenCalled();

    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "Revogar" }));
    await waitFor(() => expect(revokeDeliveryEvidence).toHaveBeenCalledWith("d1", "e1"));

    confirm.mockRestore();
  });
});
