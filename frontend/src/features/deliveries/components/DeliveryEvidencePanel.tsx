import { useCallback, useEffect, useRef, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { StatusPill } from "../../../components/StatusPill";
import { IMAGE_ACCEPT, readImageAsBase64 } from "../../../services/imageFile";
import { ApiError } from "../../../types/api";
import { saveBlob } from "../../reports/api/reportsApi";
import {
  downloadDeliveryEvidence,
  getDeliveryReceipt,
  listDeliveryEvidences,
  registerDeliveryEvidence,
  revokeDeliveryEvidence,
} from "../api/evidencesApi";
import {
  EVIDENCE_KIND_LABELS,
  type DeliveryEvidence,
  type DeliveryReceipt,
  type EvidenceKind,
} from "../types";
import { mapEvidenceErrorToMessage } from "./evidenceErrorMessages";
import "./DeliveryEvidencePanel.css";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function toMessage(error: unknown): string {
  return mapEvidenceErrorToMessage(
    error instanceof ApiError
      ? error
      : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
  );
}

/** Arquivo escolhido mais a chave de intenção que o acompanha até dar certo. */
interface PendingUpload {
  readonly file: File;
  readonly eventId: string;
}

interface DeliveryEvidencePanelProps {
  readonly deliveryId: string;
  /** Perfil pode registrar e revogar; o vínculo com a viagem é do backend. */
  readonly canOperate: boolean;
}

/**
 * Comprovante da entrega e suas evidências (OC81).
 *
 * `CONFIRMADO`: a evidência se pendura no COMPROVANTE, que só existe depois da
 * conclusão. Por isso o comprovante é carregado primeiro — sem ele não há onde
 * anexar, e o backend recusa com `DELIVERY_RECEIPT_NOT_AVAILABLE`.
 *
 * `PENDENTE DE DEFINIÇÃO`: a parte de "comunicação operacional" da OC81
 * depende dos contratos da OC82/OC84, que ainda não estão publicados — o único
 * endpoint de mensagens hoje é `/messages/interpret`, que não é vinculado a
 * entrega. Nada é inventado aqui enquanto esse contrato não existir.
 */
export function DeliveryEvidencePanel({ deliveryId, canOperate }: DeliveryEvidencePanelProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [receipt, setReceipt] = useState<DeliveryReceipt | null>(null);
  const [evidences, setEvidences] = useState<readonly DeliveryEvidence[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [kind, setKind] = useState<EvidenceKind>("PHOTO");
  const [pending, setPending] = useState<PendingUpload | null>(null);

  const carregar = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      // O comprovante primeiro: se ele não existe, não faz sentido pedir a
      // lista de evidências, que responderia o mesmo erro.
      setReceipt(await getDeliveryReceipt(deliveryId));
      const page = await listDeliveryEvidences(deliveryId, { pageSize: 100 });
      setEvidences(page.items);
    } catch (error) {
      setReceipt(null);
      setErrorMessage(toMessage(error));
    } finally {
      setIsLoading(false);
    }
  }, [deliveryId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function run(action: () => Promise<void>) {
    setIsWorking(true);
    setErrorMessage(null);

    try {
      await action();
    } catch (error) {
      setErrorMessage(toMessage(error));
    } finally {
      setIsWorking(false);
    }
  }

  /**
   * O envio e o reenvio usam a MESMA chave de intenção.
   *
   * O arquivo escolhido só é descartado depois de um registro bem-sucedido.
   * Numa falha de rede, repetir com a mesma chave devolve o registro original
   * em vez de criar uma segunda evidência igual — é o que impede a falha de
   * virar duplicata silenciosa.
   */
  function enviar() {
    if (!pending) return;

    void (async () => {
      setIsWorking(true);
      setErrorMessage(null);

      let contentBase64: string;
      try {
        contentBase64 = await readImageAsBase64(pending.file);
      } catch (error) {
        // Recusa LOCAL do arquivo. A mensagem já é específica e não passa pelo
        // mapa de códigos da API, que não conhece este caso — mandá-la para lá
        // a transformaria em "erro inesperado".
        setErrorMessage(error instanceof Error ? error.message : "Arquivo inválido.");
        setIsWorking(false);
        return;
      }

      try {
        await registerDeliveryEvidence(deliveryId, {
          eventId: pending.eventId,
          kind,
          contentBase64,
        });

        setPending(null);
        if (fileInput.current) fileInput.current.value = "";
        await carregar();
      } catch (error) {
        setErrorMessage(toMessage(error));
      } finally {
        setIsWorking(false);
      }
    })();
  }

  if (isLoading) {
    return (
      <p className="entity-state">
        <span className="spinner" aria-hidden="true" />
        <span>Carregando comprovante…</span>
      </p>
    );
  }

  if (receipt === null) {
    return (
      <>
        <AlertBanner>{errorMessage}</AlertBanner>
        <button type="button" className="btn-secondary" onClick={() => void carregar()}>
          Tentar novamente
        </button>
      </>
    );
  }

  return (
    <div className="evidence-panel">
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <dl className="evidence-receipt">
        <div>
          <dt>ENTREGUE EM</dt>
          <dd>{dateTime.format(new Date(receipt.deliveredAt))}</dd>
        </div>
        <div>
          <dt>REGISTRADO EM</dt>
          <dd>{dateTime.format(new Date(receipt.recordedAt))}</dd>
        </div>
      </dl>

      {canOperate ? (
        <form
          className="evidence-form"
          onSubmit={(event) => {
            event.preventDefault();
            enviar();
          }}
        >
          <FormField id="evidence-kind" label="TIPO" narrow>
            <select
              id="evidence-kind"
              value={kind}
              disabled={isWorking}
              onChange={(event) => setKind(event.target.value as EvidenceKind)}
            >
              <option value="PHOTO">{EVIDENCE_KIND_LABELS.PHOTO}</option>
              <option value="SIGNATURE">{EVIDENCE_KIND_LABELS.SIGNATURE}</option>
            </select>
          </FormField>

          <FormField
            id="evidence-file"
            label="IMAGEM"
            hint="PNG ou JPEG, até 5 MiB. A imagem é regravada pelo servidor, sem metadados."
          >
            <input
              id="evidence-file"
              ref={fileInput}
              type="file"
              accept={IMAGE_ACCEPT}
              disabled={isWorking}
              onChange={(event) => {
                const file = event.target.files?.[0];
                // Chave nova a cada ARQUIVO novo. Reaproveitá-la para outros
                // bytes daria EVIDENCE_IDENTITY_CONFLICT.
                setPending(file ? { file, eventId: crypto.randomUUID() } : null);
              }}
            />
          </FormField>

          <button type="submit" className="btn-primary" disabled={!pending || isWorking}>
            {isWorking ? (
              <>
                <span className="spinner" aria-hidden="true" />
                <span>Enviando…</span>
              </>
            ) : (
              <span>{errorMessage && pending ? "Tentar novamente" : "Registrar evidência"}</span>
            )}
          </button>
        </form>
      ) : null}

      {evidences.length === 0 ? (
        <p className="entity-state">Nenhuma evidência registrada para esta entrega.</p>
      ) : (
        <ul className="evidence-list">
          {evidences.map((evidence) => (
            <li key={evidence.id} className="evidence-item">
              <div className="evidence-item-head">
                <span className="evidence-kind">{EVIDENCE_KIND_LABELS[evidence.kind]}</span>
                <StatusPill tone={evidence.status === "ACTIVE" ? "good" : "neutral"}>
                  {evidence.status === "ACTIVE" ? "Ativa" : "Revogada"}
                </StatusPill>
              </div>
              <p className="evidence-meta">
                {formatSize(evidence.sizeBytes)} ·{" "}
                {dateTime.format(new Date(evidence.recordedAt))}
                {evidence.revokedAt
                  ? ` · revogada em ${dateTime.format(new Date(evidence.revokedAt))}`
                  : ""}
              </p>
              {evidence.status === "ACTIVE" ? (
                <div className="evidence-actions">
                  <button
                    type="button"
                    className="btn-link"
                    disabled={isWorking}
                    onClick={() =>
                      void run(async () => {
                        const blob = await downloadDeliveryEvidence(deliveryId, evidence.id);
                        const extensao = evidence.mediaType === "image/png" ? "png" : "jpg";
                        saveBlob(blob, `evidencia-${evidence.id}.${extensao}`);
                      })
                    }
                  >
                    Baixar
                  </button>
                  {canOperate ? (
                    <button
                      type="button"
                      className="btn-link"
                      disabled={isWorking}
                      onClick={() => {
                        // Revogação é definitiva: o contrato não prevê
                        // reativação nem substituição do arquivo. Sem a
                        // confirmação, um clique errado some com a prova da
                        // entrega e a única saída é registrar outra.
                        if (
                          !window.confirm(
                            "Revogar esta evidência? O download é bloqueado e não há como reativar.",
                          )
                        ) {
                          return;
                        }
                        void run(async () => {
                          await revokeDeliveryEvidence(deliveryId, evidence.id);
                          await carregar();
                        });
                      }}
                    >
                      Revogar
                    </button>
                  ) : null}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
