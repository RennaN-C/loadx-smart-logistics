import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { createLoadingSession } from "../api/loadingApi";
import { mapLoadingErrorToMessage } from "./loadingErrorMessages";

interface StartLoadingActionProps {
  readonly loadPlanId: string;
}

/**
 * Porta de entrada do carregamento, a partir do plano aprovado.
 *
 * `CONFIRMADO`: `POST /loading-sessions` cria OU devolve a única sessão do
 * plano. Por isso o mesmo botão serve para abrir e para voltar, e a tela não
 * precisa guardar o id em lugar nenhum. `ADMIN` e `LOGISTICS_MANAGER` criam.
 *
 * `RISCO IDENTIFICADO`: sem rota de listagem de sessões, o `CHECKER` não tem
 * como chegar aqui sozinho — ele depende de receber o link. Registrado em
 * `LoadingPage` e no README da feature.
 */
export function StartLoadingAction({ loadPlanId }: StartLoadingActionProps) {
  const navigate = useNavigate();
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function abrir() {
    setErrorMessage(null);
    setIsWorking(true);

    try {
      const session = await createLoadingSession(loadPlanId);
      navigate(`/loading/${session.id}`);
    } catch (error) {
      setErrorMessage(
        mapLoadingErrorToMessage(
          error instanceof ApiError
            ? error
            : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
        ),
      );
      setIsWorking(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="btn-secondary"
        disabled={isWorking}
        onClick={() => void abrir()}
      >
        {isWorking ? (
          <>
            <span className="spinner" aria-hidden="true" />
            <span>Abrindo…</span>
          </>
        ) : (
          <span>Conferir carregamento</span>
        )}
      </button>

      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}
    </>
  );
}
