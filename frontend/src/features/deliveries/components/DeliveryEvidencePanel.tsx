import { useRef, useState } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { saveBlob } from "../../reports/api/reportsApi";
import { downloadDeliveryEvidence, revokeDeliveryEvidence } from "../api/evidencesApi";
import { evidenceError, useDeliveryEvidence } from "../hooks/useDeliveryEvidence";
import type { DeliveryEvidence } from "../types";
import { DeliveryEvidenceList } from "./DeliveryEvidenceList";
import { DeliveryEvidenceUpload } from "./DeliveryEvidenceUpload";
import "./DeliveryEvidencePanel.css";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });
interface Props { readonly deliveryId: string; readonly canOperate: boolean }

/** A chave remonta o estado por entrega; respostas antigas nunca migram para outra operação. */
export function DeliveryEvidencePanel(props: Props) { return <EvidenceContent key={props.deliveryId} {...props} />; }

function EvidenceContent({ deliveryId, canOperate }: Props) {
  const { receipt, data, page, loading, error, load } = useDeliveryEvidence(deliveryId);
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const working = useRef(false);
  async function run(action: () => Promise<void>) {
    if (working.current) return;
    working.current = true; setBusy(true); setActionError(""); setNotice("");
    try { await action(); } catch (e) { setActionError(evidenceError(e)); }
    finally { working.current = false; setBusy(false); }
  }
  function download(evidence: DeliveryEvidence) {
    void run(async () => { const blob = await downloadDeliveryEvidence(deliveryId, evidence.id); saveBlob(blob, `evidencia-${evidence.id}.${evidence.mediaType === "image/png" ? "png" : "jpg"}`); });
  }
  function revoke(evidence: DeliveryEvidence) {
    if (!window.confirm("Revogar esta evidência? O download é bloqueado e não há como reativar.")) return;
    void run(async () => { await revokeDeliveryEvidence(deliveryId, evidence.id); setNotice("Revogação confirmada. Os metadados e o histórico foram preservados."); await load(page); });
  }
  if (loading && !receipt) return <p className="entity-state" role="status">Carregando comprovante…</p>;
  if (!receipt) return <><AlertBanner>{error}</AlertBanner><button type="button" className="btn-secondary" onClick={() => void load(page)}>Tentar novamente</button></>;
  return <div className="evidence-panel" aria-busy={loading || busy}>
    {(actionError || error) && <AlertBanner>{actionError || error}</AlertBanner>}
    {notice && <output className="evidence-notice">{notice}</output>}
    <dl className="evidence-receipt"><div><dt>ENTREGUE EM</dt><dd>{dateTime.format(new Date(receipt.deliveredAt))}</dd></div><div><dt>REGISTRADO EM</dt><dd>{dateTime.format(new Date(receipt.recordedAt))}</dd></div></dl>
    {canOperate && <DeliveryEvidenceUpload deliveryId={deliveryId} disabled={busy || loading} onError={setActionError} onRegistered={async () => { setNotice("Registro confirmado. A lista apresenta o estado atual da evidência."); await load(); }} />}
    <div className="evidence-list-header"><h3>Evidências</h3><button type="button" className="btn-secondary" disabled={busy || loading} onClick={() => void load(page)}>Atualizar evidências</button></div>
    {loading ? <p role="status">Consultando evidências…</p> : data && <DeliveryEvidenceList evidences={data.items} canOperate={canOperate} busy={busy} onDownload={download} onRevoke={revoke} />}
    {data && <fieldset className="evidence-pagination" disabled={busy || loading}><Pagination page={data.page} totalPages={data.totalPages} onChange={n => void load(n)} label="evidências" /></fieldset>}
  </div>;
}
