import { useEffect, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { ApiError } from "../../../types/api";
import { saveBlob } from "../../reports/api/reportsApi";
import { downloadAttachment, listAttachments, readAttachmentFile, revokeAttachment, uploadAttachment, type Attachment, type AttachmentResource } from "../api/attachmentsApi";

interface Props {
  resource: AttachmentResource;
  resourceId: string;
  canManage: boolean;
}
function message(error: unknown) {
  if (error instanceof ApiError && error.code === "ATTACHMENT_STORAGE_UNAVAILABLE") return "Armazenamento indisponível. Tente novamente mais tarde.";
  return error instanceof Error ? error.message : "Não foi possível acessar os anexos.";
}
export function AttachmentPanel({ resource, resourceId, canManage }: Props) {
  const [items, setItems] = useState<Attachment[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  // Keep an event identity with the selected bytes until a successful upload.
  const [pending, setPending] = useState<{ file: File; eventId: string } | null>(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    listAttachments(resource, resourceId, { page }).then((result) => {
      if (active) { setItems(result.items); setTotalPages(result.totalPages); }
    }).catch((reason: unknown) => { if (active) setError(message(reason)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [resource, resourceId, page, refresh]);
  async function run(action: () => Promise<void>) {
    setWorking(true); setError(null);
    try { await action(); } catch (reason) { setError(message(reason)); }
    finally { setWorking(false); }
  }
  return <section aria-label="Anexos operacionais">
    <p>PNG/JPEG, até 5 MiB. Remoção lógica preserva histórico.</p>
    {error ? <AlertBanner>{error}</AlertBanner> : null}
    {canManage ? <form onSubmit={(event) => {
      event.preventDefault();
      if (pending) void run(async () => {
        const content = await readAttachmentFile(pending.file);
        await uploadAttachment(resource, resourceId, pending.eventId, content);
        setPending(null); setPage(1); setRefresh((value) => value + 1);
      });
    }}>
      <label>Arquivo PNG/JPEG <input type="file" accept="image/png,image/jpeg" disabled={working} onChange={(event) => {
        const file = event.target.files?.[0];
        setPending(file ? { file, eventId: crypto.randomUUID() } : null);
      }} /></label>
      <button type="submit" className="btn-primary" disabled={!pending || working}>Enviar anexo</button>
    </form> : null}
    {loading ? <p role="status">Carregando anexos…</p> : null}
    {!loading && !error && items.length === 0 ? <p>Nenhum anexo registrado.</p> : null}
    {!loading ? <ul>{items.map((item) => <li key={item.id}>
      <span>{item.media_type} · {item.size_bytes} bytes · {new Date(item.recorded_at).toLocaleString("pt-BR")} · {item.status === "ACTIVE" ? "Ativo" : "Removido"}</span>
      {item.status === "ACTIVE" ? <>
        <button type="button" className="btn-secondary" disabled={working} onClick={() => void run(async () => {
          saveBlob(await downloadAttachment(resource, resourceId, item.id), `${item.id}.${item.media_type === "image/png" ? "png" : "jpg"}`);
        })}>Baixar anexo</button>
        {canManage ? <button type="button" className="btn-secondary" disabled={working} onClick={() => {
          if (window.confirm("Remover este anexo? O histórico será preservado e o download bloqueado.")) void run(async () => {
            await revokeAttachment(resource, resourceId, item.id); setRefresh((value) => value + 1);
          });
        }}>Remover anexo</button> : null}
      </> : null}
    </li>)}</ul> : null}
    <Pagination page={page} totalPages={totalPages} onChange={setPage} label="anexos" />
  </section>;
}
