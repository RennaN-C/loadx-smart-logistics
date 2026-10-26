import { useState } from "react";
import { Pagination } from "../../../components/Pagination";
import type { ImportPreview } from "../api/importsApi";

export function ImportPreviewTable({ preview }: { readonly preview: ImportPreview }) {
  const [page, setPage] = useState(1);
  const columns = Object.keys(preview.rows[0]?.data ?? {});
  return <section aria-label="Prévia dos cadastros">
    <p>{preview.valid_count} de {preview.row_count} linhas válidas. {preview.can_confirm ? "Arquivo pronto para confirmação." : "Corrija os erros e gere outra prévia."}</p>
    {columns.length ? <div style={{ overflowX: "auto" }}><table>
      <caption>Valores normalizados conforme o cadastro</caption>
      <thead><tr><th scope="col">Linha</th>{columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead>
      <tbody>{preview.rows.slice((page - 1) * 20, page * 20).map((row) => <tr key={row.line}>
        <th scope="row">{row.line}</th>{columns.map((column) => <td key={column}>{String(row.data[column] ?? "—")}</td>)}
      </tr>)}</tbody>
    </table></div> : null}
    <Pagination page={page} totalPages={Math.ceil(preview.rows.length / 20)} onChange={setPage} label="linhas da prévia" />
  </section>;
}
