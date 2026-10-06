import { useParams } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { StatusPill } from "../../../components/StatusPill";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { changeLoadingStatus, checkLoadingItem, scanLoadingItem } from "../api/loadingApi";
import { LoadingChecklist } from "../components/LoadingChecklist";
import { mapLoadingErrorToMessage } from "../components/loadingErrorMessages";
import { ScanField, type ScanOutcome } from "../components/ScanField";
import { useLoadingSession } from "../hooks/useLoadingSession";
import { LOADING_TRANSITIONS, type LoadingSession, type LoadingSessionStatus } from "../types";
import "./LoadingPage.css";

const STATUS_LABELS: Record<LoadingSessionStatus, string> = {
  PENDING: "Não iniciado",
  IN_PROGRESS: "Em conferência",
  FINISHED: "Concluído",
};

const ACTION_LABELS: Record<LoadingSessionStatus, string> = {
  PENDING: "Iniciar conferência",
  IN_PROGRESS: "Finalizar carregamento",
  FINISHED: "",
};

function statusTone(status: LoadingSessionStatus) {
  if (status === "FINISHED") return "good" as const;
  return status === "IN_PROGRESS" ? "warn" as const : "neutral" as const;
}

/**
 * Conferência do carregamento (OC32) com leitura de código (OC75).
 *
 * `CONFIRMADO` (OC66): somente `CHECKER` inicia, confere e finaliza. `ADMIN` e
 * `LOGISTICS_MANAGER` leem o checklist e não recebem ação nenhuma — esconder o
 * botão não substitui o backend, que continua respondendo 403, só evita
 * oferecer um caminho que terminaria em recusa.
 *
 * `RISCO IDENTIFICADO`: não existe rota de LISTAGEM de sessões, e o plano não
 * expõe o id da sessão. O gestor chega aqui pelo plano aprovado, que cria ou
 * devolve a sessão; o conferente depende de receber o link. Enquanto o backend
 * não oferecer uma porta de entrada por perfil, o `CHECKER` não acha o próprio
 * carregamento sozinho — a mesma lacuna que o motorista teve antes do
 * `GET /trips`.
 */
export function LoadingPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { user } = useAuth();
  const { session, rows, pendingCount, isLoading, isWorking, errorMessage, run, reload } =
    useLoadingSession(sessionId);

  const isChecker = user?.role === "CHECKER";
  const inProgress = session?.status === "IN_PROGRESS";
  const nextStatus = session ? LOADING_TRANSITIONS[session.status] : undefined;
  const canFinish = session?.status !== "IN_PROGRESS" || pendingCount === 0;

  /**
   * Diz QUAL volume entrou. O backend devolve a sessão inteira, então o volume
   * recém-conferido é o que mudou de pendente para conferido entre as duas
   * versões — não dá para deduzir do código lido sem repetir no cliente a
   * decisão que é do servidor.
   */
  function describeScan(antes: LoadingSession, depois: LoadingSession): string {
    const pendentes = new Set(
      antes.items.filter((item) => item.status === "PENDING").map((item) => item.id),
    );
    const novo = depois.items.find(
      (item) => item.status === "CHECKED" && pendentes.has(item.id),
    );
    const linha = rows.find((row) => row.itemId === novo?.id);
    const nome = linha?.product?.productName;

    const restantes = depois.items.filter((item) => item.status === "PENDING").length;
    const conferido = nome ? `Conferido: ${nome}.` : "Volume conferido.";

    return restantes === 0
      ? `${conferido} Era o último — o checklist está completo.`
      : `${conferido} Faltam ${restantes}.`;
  }

  async function handleScan(code: string): Promise<ScanOutcome> {
    if (!session) return { ok: false, message: "Carregamento não carregado." };

    try {
      const atualizada = await scanLoadingItem(session.id, code);
      const message = describeScan(session, atualizada);
      await run(() => Promise.resolve(atualizada));
      return { ok: true, message };
    } catch (error) {
      return {
        ok: false,
        message: mapLoadingErrorToMessage(
          error instanceof ApiError
            ? error
            : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
        ),
      };
    }
  }

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Conferência do carregamento</h1>
          <p className="entity-lede">
            Leia o código de cada volume ou confira na lista. A ordem é a de carregamento.
          </p>
        </div>
        {session ? (
          <div className="entity-toolbar">
            <StatusPill tone={statusTone(session.status)}>
              {STATUS_LABELS[session.status]}
            </StatusPill>
          </div>
        ) : null}
      </header>

      {errorMessage ? (
        <>
          <AlertBanner>{errorMessage}</AlertBanner>
          <button type="button" className="btn-secondary" onClick={reload}>
            Tentar novamente
          </button>
        </>
      ) : null}

      {isLoading ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando conferência…</span>
        </p>
      ) : null}

      {session && !isLoading ? (
        <>
          <section className="loading-head">
            <dl className="loading-metrics">
              <div>
                <dt>VOLUMES</dt>
                <dd>{rows.length}</dd>
              </div>
              <div>
                <dt>PENDENTES</dt>
                <dd className={pendingCount > 0 ? "loading-pending-warn" : undefined}>
                  {pendingCount}
                </dd>
              </div>
            </dl>

            {isChecker && nextStatus ? (
              <button
                type="button"
                className="btn-primary"
                disabled={isWorking || !canFinish}
                title={canFinish ? undefined : "Ainda há volumes pendentes"}
                onClick={() => void run(() => changeLoadingStatus(session.id, nextStatus))}
              >
                {isWorking ? (
                  <>
                    <span className="spinner" aria-hidden="true" />
                    <span>Processando…</span>
                  </>
                ) : (
                  <span>{ACTION_LABELS[session.status]}</span>
                )}
              </button>
            ) : null}
          </section>

          {isChecker ? (
            <ScanField
              disabled={!inProgress}
              disabledReason={
                session.status === "PENDING"
                  ? "Inicie a conferência para começar a ler os códigos."
                  : "Este carregamento já foi concluído."
              }
              onScan={handleScan}
            />
          ) : (
            <p className="entity-form-help">
              Somente o conferente registra a conferência. Aqui você acompanha o checklist.
            </p>
          )}

          <LoadingChecklist
            rows={rows}
            canCheck={isChecker && inProgress}
            isWorking={isWorking}
            onCheck={(itemId) => void run(() => checkLoadingItem(session.id, itemId))}
          />
        </>
      ) : null}
    </div>
  );
}
