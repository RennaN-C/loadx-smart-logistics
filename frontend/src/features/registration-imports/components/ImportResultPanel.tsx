import { useState } from "react";
import { Pagination } from "../../../components/Pagination";
import { AuditTrail } from "../../audit/components/AuditTrail";
import type { ImportResult } from "../api/importsApi";
import { ImportErrors } from "./ImportErrors";

export function ImportResultPanel({ result }: { readonly result: ImportResult }) {
  const [page, setPage] = useState(1);
  return <section aria-label="Resultado da importação">
    <h3>{result.status === "COMPLETED" ? "Importação concluída" : "Arquivo rejeitado"}</h3>
    <p>{result.created_count} cadastros criados; {result.rejected_count} linhas rejeitadas.</p>
    <p>Resultado: {result.id} · {new Date(result.recorded_at).toLocaleString("pt-BR")}</p>
    {result.errors.length ? <ImportErrors key={result.id} errors={result.errors} /> : null}
    {result.records.length ? <>
      <h4>Cadastros criados por linha</h4>
      <ul>{result.records.slice((page - 1) * 20, page * 20).map((record) => <li key={record.id}>Linha {record.line}: {record.id}</li>)}</ul>
      <Pagination page={page} totalPages={Math.ceil(result.records.length / 20)} onChange={setPage} label="cadastros criados" />
    </> : null}
    <AuditTrail entityType="REGISTRATION_IMPORT" entityId={result.id} title="Auditoria da importação" />
  </section>;
}
