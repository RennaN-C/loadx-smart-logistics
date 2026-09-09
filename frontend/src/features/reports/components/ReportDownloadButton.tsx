import { useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Icon } from "../../../components/Icon";
import { ApiError } from "../../../types/api";
import { saveBlob } from "../api/reportsApi";
import { mapReportErrorToMessage } from "./reportsErrorMessages";

interface ReportDownloadButtonProps {
  readonly label: string;
  readonly filename: string;
  readonly download: () => Promise<Blob>;
}

/**
 * Botão de download de PDF, com o estado de espera e o erro no próprio lugar.
 *
 * O erro fica ao lado do botão, e não num alerta no topo da tela: quem clicou
 * está olhando para o botão, e o relatório de carregamento falha por um motivo
 * bem concreto — carregamento ainda não registrado — que precisa ser lido ali.
 */
export function ReportDownloadButton({ label, filename, download }: ReportDownloadButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleClick() {
    setErrorMessage(null);
    setIsDownloading(true);

    try {
      saveBlob(await download(), filename);
    } catch (error) {
      setErrorMessage(
        mapReportErrorToMessage(
          error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Falhou."),
        ),
      );
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="btn-secondary"
        disabled={isDownloading}
        onClick={() => void handleClick()}
      >
        {isDownloading ? (
          <>
            <span className="spinner" aria-hidden="true" />
            <span>Gerando…</span>
          </>
        ) : (
          <>
            <Icon name="report" size={16} />
            <span>{label}</span>
          </>
        )}
      </button>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}
    </>
  );
}
