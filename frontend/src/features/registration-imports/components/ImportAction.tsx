import { useState } from "react";
import { Modal } from "../../../components/Modal";
import type { ImportEntity } from "../api/importsApi";
import { ImportPanel } from "./ImportPanel";
const labels: Record<ImportEntity, string> = { customers: "clientes", products: "produtos", trucks: "caminhões", drivers: "motoristas" };
export function ImportAction({ entity, onImported, enabled = true }: { readonly entity: ImportEntity; readonly enabled?: boolean; readonly onImported: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  if (!enabled) return null;
  return <>
    <button type="button" className="btn-secondary" onClick={() => setOpen(true)}>Importar {labels[entity]}</button>
    {open ? <Modal title={`Importar ${labels[entity]}`} onClose={() => setOpen(false)}><ImportPanel key={entity} entity={entity} onImported={onImported} /></Modal> : null}
  </>;
}
