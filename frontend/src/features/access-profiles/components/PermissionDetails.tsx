import type { PermissionDefinition } from "../api/profilesApi";

import { MODULE_LABELS, permissionGroups } from "./profilePresentation";

export function PermissionDetails({ permissions, catalog, expanded = false }: { readonly expanded?: boolean; readonly permissions: string[]; readonly catalog: PermissionDefinition[] }) {
  const selected = catalog.filter((item) => permissions.includes(item.code));
  return <details className="access-permission-details" open={expanded}><summary>Ver permissões <span>{permissions.length}</span></summary>
    <div className="access-permission-modules">{permissionGroups(selected).map(([module, items]) => <details key={module}><summary>{MODULE_LABELS[module] ?? "Outras ações"}<span>{items.length}</span></summary><ul>{items.map((item) => <li key={item.code}>{item.label}</li>)}</ul></details>)}</div>
    {!permissions.length ? <p className="user-muted">Nenhuma ação autorizada por este perfil.</p> : null}
    {selected.length < permissions.length ? <p className="user-muted">Algumas ações não estão disponíveis no catálogo atual. Atualize a consulta.</p> : null}
  </details>;
}
