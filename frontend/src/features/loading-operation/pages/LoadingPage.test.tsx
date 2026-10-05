import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import type { Role } from "../../auth/types";
import { getLoadPlan } from "../../load-planning/api/loadPlansApi";
import type { LoadPlan, LoadPlanItem } from "../../load-planning/types";
import {
  changeLoadingStatus,
  checkLoadingItem,
  getLoadingSession,
  scanLoadingItem,
} from "../api/loadingApi";
import type { LoadingSession } from "../types";
import { LoadingPage } from "./LoadingPage";

vi.mock("../api/loadingApi");
vi.mock("../../load-planning/api/loadPlansApi");
vi.mock("../../auth/hooks/useAuth");

const CODIGO_1 = "loadx:loading-item:11111111-1111-4111-8111-111111111111";
const CODIGO_2 = "loadx:loading-item:22222222-2222-4222-8222-222222222222";

function sessao(overrides: Partial<LoadingSession> = {}): LoadingSession {
  return {
    id: "ls1",
    loadPlanId: "lp1",
    status: "IN_PROGRESS",
    startedAt: "2026-10-05T10:00:00Z",
    finishedAt: null,
    items: [
      { id: "i1", loadPlanItemId: "pi1", status: "PENDING", code: CODIGO_1 },
      { id: "i2", loadPlanItemId: "pi2", status: "PENDING", code: CODIGO_2 },
    ],
    ...overrides,
  };
}

function planItem(id: string, nome: string, seq: number): LoadPlanItem {
  return {
    id,
    orderId: "o1",
    orderItemId: "oi1",
    productId: "p1",
    volumeIndex: 1,
    quantity: 1,
    deliverySequence: 1,
    productCode: `COD-${seq}`,
    productName: nome,
    originalWidthCm: 40,
    originalHeightCm: 30,
    originalLengthCm: 60,
    weightKg: 10,
    fragile: false,
    stackable: true,
    rotationAllowed: true,
    placed: true,
    loadingSequence: seq,
  } as unknown as LoadPlanItem;
}

function mockRole(role: Role) {
  vi.mocked(useAuth).mockReturnValue({
    status: "authenticated",
    user: {
      id: "u1",
      name: "Ana Souza",
      email: "ana@example.test",
      role,
      active: true,
      createdAt: "2026-08-01T00:00:00Z",
    },
    login: vi.fn(),
    logout: vi.fn(),
  });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/loading/ls1"]}>
      <Routes>
        <Route path="/loading/:sessionId" element={<LoadingPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Simula o leitor físico: ele digita o código inteiro e manda Enter. */
function lerCodigo(code: string) {
  const campo = screen.getByLabelText("LER CÓDIGO DO VOLUME");
  fireEvent.change(campo, { target: { value: code } });
  fireEvent.submit(campo.closest("form") as HTMLFormElement);
}

beforeEach(() => {
  vi.mocked(getLoadingSession).mockResolvedValue(sessao());
  vi.mocked(getLoadPlan).mockResolvedValue({
    id: "lp1",
    items: [planItem("pi1", "Televisor 50", 1), planItem("pi2", "Geladeira Frost", 2)],
  } as unknown as LoadPlan);
  vi.mocked(scanLoadingItem).mockReset();
  vi.mocked(checkLoadingItem).mockReset();
  vi.mocked(changeLoadingStatus).mockReset();
});

describe("LoadingPage — checklist", () => {
  it("mostra o produto de cada volume, e não o UUID do item", async () => {
    // O backend guarda só id/status no checklist; sem a junção com o plano o
    // conferente receberia uma lista de UUIDs.
    mockRole("CHECKER");
    renderPage();

    expect(await screen.findByText("Televisor 50")).toBeInTheDocument();
    expect(screen.getByText("Geladeira Frost")).toBeInTheDocument();
  });

  it("ordena pela sequência de CARREGAMENTO, que é como os volumes aparecem na doca", async () => {
    mockRole("CHECKER");
    vi.mocked(getLoadPlan).mockResolvedValue({
      id: "lp1",
      items: [planItem("pi1", "Televisor 50", 9), planItem("pi2", "Geladeira Frost", 2)],
    } as unknown as LoadPlan);

    renderPage();
    await screen.findByText("Geladeira Frost");

    const linhas = screen.getAllByRole("row").slice(1);
    expect(within(linhas[0]).getByText("Geladeira Frost")).toBeInTheDocument();
  });

  it("continua conferível quando o plano não carrega: o volume não some da lista", async () => {
    // Sem o plano perde-se o nome do produto, não o volume. Uma linha a menos
    // faria o checklist mentir sobre quantos volumes existem.
    mockRole("CHECKER");
    vi.mocked(getLoadPlan).mockRejectedValue(new ApiError("AUTH_FORBIDDEN", "negado"));

    renderPage();

    expect(await screen.findAllByText("Volume sem descrição no plano")).toHaveLength(2);
  });
});

describe("LoadingPage — permissões (OC66)", () => {
  it("o conferente recebe o campo de leitura", async () => {
    mockRole("CHECKER");
    renderPage();

    expect(await screen.findByLabelText("LER CÓDIGO DO VOLUME")).toBeInTheDocument();
  });

  it("o gestor acompanha o checklist, sem ação nenhuma", async () => {
    // Esconder não substitui o backend, que responde 403; evita só oferecer um
    // caminho que terminaria em recusa.
    mockRole("LOGISTICS_MANAGER");
    renderPage();

    await screen.findByText("Televisor 50");
    expect(screen.queryByLabelText("LER CÓDIGO DO VOLUME")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Conferir / })).not.toBeInTheDocument();
    expect(screen.getByText(/Somente o conferente registra/)).toBeInTheDocument();
  });
});

describe("LoadingPage — leitura de código (OC75)", () => {
  it("confere o volume e diz QUAL entrou e quantos faltam", async () => {
    mockRole("CHECKER");
    const depois = sessao({
      items: [
        { id: "i1", loadPlanItemId: "pi1", status: "CHECKED", code: CODIGO_1 },
        { id: "i2", loadPlanItemId: "pi2", status: "PENDING", code: CODIGO_2 },
      ],
    });
    vi.mocked(scanLoadingItem).mockResolvedValue(depois);

    renderPage();
    await screen.findByText("Televisor 50");
    lerCodigo(CODIGO_1);

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Conferido: Televisor 50. Faltam 1.",
    );
    expect(vi.mocked(scanLoadingItem).mock.calls[0]).toEqual(["ls1", CODIGO_1]);
  });

  it("avisa quando foi o último volume", async () => {
    mockRole("CHECKER");
    vi.mocked(scanLoadingItem).mockResolvedValue(
      sessao({
        items: [
          { id: "i1", loadPlanItemId: "pi1", status: "CHECKED", code: CODIGO_1 },
          { id: "i2", loadPlanItemId: "pi2", status: "CHECKED", code: CODIGO_2 },
        ],
      }),
    );

    renderPage();
    await screen.findByText("Televisor 50");
    lerCodigo(CODIGO_2);

    expect(await screen.findByRole("status")).toHaveTextContent(/último/);
  });

  it("recusa formato inválido SEM ir ao servidor", async () => {
    // Um leitor físico pode entregar lixo, e o campo também aceita digitação.
    // Gastar uma requisição com algo que nem parece código do sistema atrasa
    // quem está lendo volume atrás de volume.
    mockRole("CHECKER");
    renderPage();
    await screen.findByText("Televisor 50");

    lerCodigo("7891234567890");

    expect(await screen.findByRole("status")).toHaveTextContent(/não reconhecido/i);
    expect(scanLoadingItem).not.toHaveBeenCalled();
  });

  it("não aceita UUID em maiúsculas: o backend exige a forma canônica", async () => {
    mockRole("CHECKER");
    renderPage();
    await screen.findByText("Televisor 50");

    lerCodigo("loadx:loading-item:11111111-1111-4111-8111-11111111111A");

    expect(await screen.findByRole("status")).toHaveTextContent(/não reconhecido/i);
    expect(scanLoadingItem).not.toHaveBeenCalled();
  });

  it("explica a leitura repetida em vez de marcar outro volume", async () => {
    mockRole("CHECKER");
    vi.mocked(scanLoadingItem).mockRejectedValue(
      new ApiError("LOADING_ITEM_ALREADY_CHECKED", "Item já conferido.", [], 409),
    );

    renderPage();
    await screen.findByText("Televisor 50");
    lerCodigo(CODIGO_1);

    expect(await screen.findByRole("status")).toHaveTextContent(/já estava conferido/i);
    // nada mudou na lista
    expect(screen.getAllByText("Pendente")).toHaveLength(2);
  });

  it("diz que o volume é de OUTRO carregamento", async () => {
    mockRole("CHECKER");
    vi.mocked(scanLoadingItem).mockRejectedValue(
      new ApiError("LOADING_ITEM_SESSION_MISMATCH", "Item não pertence à sessão.", [], 409),
    );

    renderPage();
    await screen.findByText("Televisor 50");
    lerCodigo(CODIGO_2);

    expect(await screen.findByRole("status")).toHaveTextContent(/OUTRO carregamento/);
  });

  it("código de volume inexistente não vira erro genérico", async () => {
    mockRole("CHECKER");
    vi.mocked(scanLoadingItem).mockRejectedValue(
      new ApiError("LOADING_ITEM_NOT_FOUND", "Item não encontrado.", [], 404),
    );

    renderPage();
    await screen.findByText("Televisor 50");
    lerCodigo(CODIGO_1);

    expect(await screen.findByRole("status")).toHaveTextContent(/Nenhum volume corresponde/);
  });

  it("o campo se limpa e volta a receber foco, para a próxima leitura", async () => {
    mockRole("CHECKER");
    vi.mocked(scanLoadingItem).mockResolvedValue(sessao());

    renderPage();
    await screen.findByText("Televisor 50");
    lerCodigo(CODIGO_1);

    const campo = await screen.findByLabelText<HTMLInputElement>("LER CÓDIGO DO VOLUME");
    await waitFor(() => expect(campo.value).toBe(""));
    expect(campo).toHaveFocus();
  });

  it("o campo fica travado enquanto a conferência não começou", async () => {
    mockRole("CHECKER");
    vi.mocked(getLoadingSession).mockResolvedValue(sessao({ status: "PENDING" }));

    renderPage();

    expect(await screen.findByLabelText("LER CÓDIGO DO VOLUME")).toBeDisabled();
    expect(screen.getByText(/Inicie a conferência/)).toBeInTheDocument();
  });
});

describe("LoadingPage — fluxo manual e etapas", () => {
  it("mantém a conferência manual ao lado da leitura", async () => {
    // Etiqueta rasgada e leitor sem bateria são a razão de o caminho manual
    // não poder sumir.
    mockRole("CHECKER");
    vi.mocked(checkLoadingItem).mockResolvedValue(sessao());

    renderPage();
    await screen.findByText("Televisor 50");

    fireEvent.click(screen.getByRole("button", { name: "Conferir Televisor 50" }));

    await waitFor(() => expect(vi.mocked(checkLoadingItem).mock.calls[0]).toEqual(["ls1", "i1"]));
  });

  it("não finaliza com volume pendente", async () => {
    mockRole("CHECKER");
    renderPage();
    await screen.findByText("Televisor 50");

    expect(screen.getByRole("button", { name: "Finalizar carregamento" })).toBeDisabled();
  });

  it("libera a finalização com o checklist completo", async () => {
    mockRole("CHECKER");
    vi.mocked(getLoadingSession).mockResolvedValue(
      sessao({
        items: [
          { id: "i1", loadPlanItemId: "pi1", status: "CHECKED", code: CODIGO_1 },
          { id: "i2", loadPlanItemId: "pi2", status: "CHECKED", code: CODIGO_2 },
        ],
      }),
    );

    renderPage();
    await screen.findByText("Televisor 50");

    const botao = screen.getByRole("button", { name: "Finalizar carregamento" });
    expect(botao).toBeEnabled();

    vi.mocked(changeLoadingStatus).mockResolvedValue(sessao({ status: "FINISHED" }));
    fireEvent.click(botao);

    await waitFor(() =>
      expect(vi.mocked(changeLoadingStatus).mock.calls[0]).toEqual(["ls1", "FINISHED"]),
    );
  });

  it("começa oferecendo iniciar a conferência", async () => {
    mockRole("CHECKER");
    vi.mocked(getLoadingSession).mockResolvedValue(sessao({ status: "PENDING" }));

    renderPage();

    expect(await screen.findByRole("button", { name: "Iniciar conferência" })).toBeEnabled();
  });

  it("concluído não oferece mais ação", async () => {
    mockRole("CHECKER");
    vi.mocked(getLoadingSession).mockResolvedValue(sessao({ status: "FINISHED" }));

    renderPage();
    await screen.findByText("Televisor 50");

    expect(screen.queryByRole("button", { name: /Finalizar|Iniciar/ })).not.toBeInTheDocument();
  });

  it("oferece nova tentativa quando a sessão não carrega", async () => {
    mockRole("CHECKER");
    vi.mocked(getLoadingSession).mockRejectedValue(
      new ApiError("LOADING_SESSION_NOT_FOUND", "não encontrada", [], 404),
    );

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(/não existe mais/);
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});
