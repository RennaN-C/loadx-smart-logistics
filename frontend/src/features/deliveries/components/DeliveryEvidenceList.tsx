import { StatusPill } from "../../../components/StatusPill";
import { EVIDENCE_KIND_LABELS, type DeliveryEvidence } from "../types";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });
function size(bytes: number): string { return bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`; }
interface Props {
  readonly evidences: readonly DeliveryEvidence[];
  readonly canOperate: boolean;
  readonly busy: boolean;
  readonly onDownload: (evidence: DeliveryEvidence) => void;
  readonly onRevoke: (evidence: DeliveryEvidence) => void;
}
export function DeliveryEvidenceList({ evidences, canOperate, busy, onDownload, onRevoke }: Props) {
  if (!evidences.length) return <p className="entity-state">Nenhuma evidência registrada para esta entrega.</p>;
  return <ul className="evidence-list">{evidences.map(evidence => <li key={evidence.id} className="evidence-item">
    <div className="evidence-item-head"><span className="evidence-kind">{EVIDENCE_KIND_LABELS[evidence.kind]}</span><StatusPill tone={evidence.status === "ACTIVE" ? "good" : "neutral"}>{evidence.status === "ACTIVE" ? "Ativa" : "Revogada"}</StatusPill></div>
    <p className="evidence-meta">{size(evidence.sizeBytes)} · {dateTime.format(new Date(evidence.recordedAt))}{evidence.revokedAt ? ` · revogada em ${dateTime.format(new Date(evidence.revokedAt))}` : ""}</p>
    {evidence.status === "ACTIVE" && <div className="evidence-actions"><button type="button" className="btn-link" disabled={busy} onClick={() => onDownload(evidence)}>Baixar</button>{canOperate && <button type="button" className="btn-link" disabled={busy} onClick={() => onRevoke(evidence)}>Revogar</button>}</div>}
  </li>)}</ul>;
}
