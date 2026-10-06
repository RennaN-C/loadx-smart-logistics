import { api } from "../../../services/api";
import type {
  LoadingItemStatus,
  LoadingSession,
  LoadingSessionItem,
  LoadingSessionStatus,
} from "../types";

/**
 * Carregamento (OC32) e conferência por código (OC75/OC76).
 *
 * Todas as rotas devolvem a SESSÃO INTEIRA, inclusive as de conferir item e ler
 * código. Isso é de propósito no backend e a tela se apoia nisso: depois de
 * cada ação o checklist vem recalculado pelo servidor, então não existe estado
 * derivado no cliente para divergir — nem contador de pendentes, nem "pode
 * finalizar", que saem da lista recebida.
 */

interface LoadingSessionItemDto {
  id: string;
  load_plan_item_id: string;
  status: LoadingItemStatus;
  code: string;
}

interface LoadingSessionDto {
  id: string;
  load_plan_id: string;
  status: LoadingSessionStatus;
  started_at: string | null;
  finished_at: string | null;
  items: LoadingSessionItemDto[];
}

function mapItem(dto: LoadingSessionItemDto): LoadingSessionItem {
  return {
    id: dto.id,
    loadPlanItemId: dto.load_plan_item_id,
    status: dto.status,
    code: dto.code,
  };
}

function mapSession(dto: LoadingSessionDto): LoadingSession {
  return {
    id: dto.id,
    loadPlanId: dto.load_plan_id,
    status: dto.status,
    startedAt: dto.started_at,
    finishedAt: dto.finished_at,
    items: dto.items.map(mapItem),
  };
}

/**
 * Cria a sessão do plano, ou devolve a que já existe.
 *
 * `CONFIRMADO`: o backend trata a chamada como idempotente — "cria ou retorna a
 * única sessão do plano APPROVED". É o que permite o gestor voltar ao
 * carregamento pelo mesmo botão, sem a tela precisar guardar o id em lugar
 * nenhum. Somente `LOGISTICS_MANAGER`.
 */
export async function createLoadingSession(loadPlanId: string): Promise<LoadingSession> {
  const { data } = await api.post<LoadingSessionDto>("/loading-sessions", {
    load_plan_id: loadPlanId,
  });

  return mapSession(data);
}

export async function getLoadingSession(sessionId: string): Promise<LoadingSession> {
  const { data } = await api.get<LoadingSessionDto>(`/loading-sessions/${sessionId}`);

  return mapSession(data);
}

/** `IN_PROGRESS` inicia a conferência e `FINISHED` encerra. Somente `CHECKER`. */
export async function changeLoadingStatus(
  sessionId: string,
  status: LoadingSessionStatus,
): Promise<LoadingSession> {
  const { data } = await api.patch<LoadingSessionDto>(`/loading-sessions/${sessionId}/status`, {
    status,
  });

  return mapSession(data);
}

/** Conferência manual de um item. Somente `CHECKER`. */
export async function checkLoadingItem(
  sessionId: string,
  itemId: string,
): Promise<LoadingSession> {
  const { data } = await api.patch<LoadingSessionDto>(
    `/loading-sessions/${sessionId}/items/${itemId}`,
    { status: "CHECKED" },
  );

  return mapSession(data);
}

/**
 * Conferência por QR Code ou código de barras (OC75).
 *
 * O código vai como veio — `loadx:loading-item:<uuid>` —, sem o frontend
 * extrair o UUID nem remontar o texto. Quem decide qual item foi lido é o
 * backend: o código IDENTIFICA, não autoriza, e repetir essa leitura aqui
 * abriria espaço para a tela marcar um item que o servidor recusaria.
 */
export async function scanLoadingItem(
  sessionId: string,
  code: string,
): Promise<LoadingSession> {
  const { data } = await api.post<LoadingSessionDto>(`/loading-sessions/${sessionId}/scan`, {
    code,
  });

  return mapSession(data);
}
