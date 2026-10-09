import { useEffect, useState } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { saveBlob } from "../../reports/api/reportsApi";
import { confirmImport, downloadImportTemplate, getImport, listImports, previewImport, readCsvFile, type ImportEntity, type ImportFile, type ImportPreview, type ImportResult, type ImportSummary } from "../api/importsApi";
import { ImportErrors } from "./ImportErrors";
import { ImportPreviewTable } from "./ImportPreviewTable";
import { ImportResultPanel } from "./ImportResultPanel";

interface Props { readonly entity: ImportEntity; readonly onImported: () => Promise<void> }
interface ReadyImport { readonly file: ImportFile; readonly preview: ImportPreview; readonly eventId: string }
export function ImportPanel({ entity, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [ready, setReady] = useState<ReadyImport | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ImportSummary[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setHistoryError(null);
    listImports(entity, { page }).then((data) => {
      if (active) { setHistory(data.items); setTotalPages(data.totalPages); }
    }).catch((reason: unknown) => { if (active) setHistoryError(reason instanceof Error ? reason.message : "Não foi possível consultar importações."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [entity, page, refresh]);
  async function run(action: () => Promise<void>) {
    setWorking(true); setError(null);
    try { await action(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível importar o arquivo."); }
    finally { setWorking(false); }
  }
  return <section className="import-panel" aria-label="Importação de cadastros">
    <p>CSV UTF-8, vírgula ou ponto-e-vírgula; até 1 MiB e 1000 registros. Cria novos cadastros. Um erro rejeita o arquivo inteiro.</p>
    <p>Use os cabeçalhos do modelo, cm/kg, decimais com ponto, true/false e datas ISO com timezone. active=false cria cadastro arquivado.</p>
    {error ? <AlertBanner>{error}</AlertBanner> : null}
    <div className="import-panel-controls" role="group" aria-label="Controles de importação CSV">
      <button type="button" className="btn-secondary" disabled={working} onClick={() => void run(async () => {
        saveBlob(await downloadImportTemplate(entity), `${entity}-modelo.csv`);
      })}>Baixar modelo CSV</button>
      <label className="import-panel-file">Arquivo CSV
        <input type="file" accept=".csv,text/csv" disabled={working} onChange={(event) => {
          setFile(event.target.files?.[0] ?? null); setReady(null); setResult(null); setError(null);
        }} />
      </label>
      <button type="button" className="btn-secondary" disabled={!file || working} onClick={() => void run(async () => {
        if (!file) return;
        setReady(null); setResult(null);
        const data = await readCsvFile(file);
        const view = await previewImport(entity, data);
        setReady({ file: data, preview: view, eventId: crypto.randomUUID() });
      })}>Validar e gerar prévia</button>
    </div>
    {working ? <output>Processando importação…</output> : null}
    {ready ? <>
      <ImportPreviewTable key={ready.eventId} preview={ready.preview} />
      {ready.preview.errors.length ? <ImportErrors key={ready.eventId} errors={ready.preview.errors} /> : null}
      <button type="button" className="btn-primary" disabled={!ready.preview.can_confirm || working || result !== null} onClick={() => void run(async () => {
        const confirmed = await confirmImport(entity, ready.file, ready.preview.sha256, ready.eventId);
        setResult(confirmed); setRefresh((value) => value + 1);
        if (confirmed.status === "COMPLETED") {
          try { await onImported(); } catch { setError("Importação concluída; não foi possível atualizar a lista de cadastros."); }
        }
      })}>Confirmar importação</button>
    </> : null}
    {result ? <ImportResultPanel key={result.id} result={result} /> : null}
    <h3>Histórico de importações</h3>
    {loading ? <output>Carregando histórico…</output> : null}
    {historyError ? <AlertBanner>{historyError}</AlertBanner> : null}
    {!loading && !historyError && !history.length ? <p>Nenhuma importação registrada.</p> : null}
    {!loading ? <ul>{history.map((item) => <li key={item.id}>
      {new Date(item.recorded_at).toLocaleString("pt-BR")} · {item.status === "COMPLETED" ? "Concluída" : "Rejeitada"} · {item.created_count}/{item.row_count} criados
      <button type="button" className="btn-secondary" disabled={working} onClick={() => void run(async () => { setResult(await getImport(item.id)); })}>Ver resultado</button>
    </li>)}</ul> : null}
    <Pagination page={page} totalPages={totalPages} onChange={setPage} label="importações" />
  </section>;
}
