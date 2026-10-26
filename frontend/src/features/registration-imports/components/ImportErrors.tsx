import { useState } from "react";
import { Pagination } from "../../../components/Pagination";
import type { ImportRowError } from "../api/importsApi";

export function ImportErrors({ errors }: { readonly errors: ImportRowError[] }) {
  const [page, setPage] = useState(1);
  return <section aria-label="Erros do arquivo">
    <h3>Erros por linha e campo ({errors.length})</h3>
    <ul>{errors.slice((page - 1) * 20, page * 20).map((error, index) => <li key={`${error.line}:${error.field}:${error.code}:${index}`}>
      {error.line === 0 ? "Arquivo" : `Linha ${error.line}`} · {error.field}: {error.message} ({error.code})
    </li>)}</ul>
    <Pagination page={page} totalPages={Math.ceil(errors.length / 20)} onChange={setPage} label="erros" />
  </section>;
}
