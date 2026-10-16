import { useCallback, useState } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Icon } from "../../../components/Icon";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useEditTarget } from "../../../hooks/useEditTarget";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { useAuth } from "../../auth/hooks/useAuth";
import type { Role } from "../../auth/types";
import { getUser, listUsers, type UserAccount } from "../api/usersApi";
import { UserEditor } from "./UserEditor";
import { ROLE_LABELS, userError } from "./userPresentation";
import "./UserManagement.css";

export function UserManagementPanel() {
  const { user, updateUser: updateSession } = useAuth();
  const [filters, setFilters] = useState({ search: "", role: "all", active: "all", sortOrder: "desc" as "asc" | "desc" });
  const load = useCallback((params: ListParams) => listUsers({ ...params, search: filters.search, sortOrder: filters.sortOrder, ...(filters.role !== "all" ? { role: filters.role as Role } : {}), ...(filters.active !== "all" ? { active: filters.active === "true" } : {}) }), [filters]);
  const list = useResourceList(load, user?.role === "ADMIN" && user.active);
  const edit = useEditTarget(getUser);
  const [creating, setCreating] = useState(false); const [notice, setNotice] = useState("");
  function filter(next: typeof filters) { setFilters(next); list.goToPage(1); }
  function close() { setCreating(false); edit.close(); }
  function saved(account: UserAccount, revoked: boolean) {
    const wasCreating = creating; close();
    if (account.id === user?.id) {
      if (revoked) { updateSession(null, "session-revoked"); return; }
      const { id, name, email, role, active, createdAt, permissions, customProfileId, customProfileName } = account;
      updateSession({ id, name, email, role, active, createdAt, permissions, customProfileId, customProfileName });
    }
    setNotice(wasCreating ? "Usuário criado com sucesso." : "Usuário atualizado com sucesso."); void list.refetch();
  }
  if (!user?.active || user.role !== "ADMIN") return null;
  return <div className="user-management">
    <div className="user-toolbar"><p className="user-muted">Contas de acesso ao LoadX. Os perfis mantêm as permissões definidas pelo sistema.</p><button type="button" className="btn-primary" disabled={edit.loadingId !== null} onClick={() => { setNotice(""); setCreating(true); }}><Icon name="plus" size={18} />Criar usuário</button></div>
    <div className="user-filters">
      <label>Buscar por nome<input type="search" maxLength={120} value={filters.search} placeholder="Nome da pessoa" onChange={(event) => filter({ ...filters, search: event.target.value })} /></label>
      <label>Filtrar perfil<select value={filters.role} onChange={(event) => filter({ ...filters, role: event.target.value })}><option value="all">Todos os perfis</option>{Object.entries(ROLE_LABELS).map(([role, label]) => <option key={role} value={role}>{label}</option>)}</select></label>
      <label>Filtrar estado<select value={filters.active} onChange={(event) => filter({ ...filters, active: event.target.value })}><option value="all">Ativos e inativos</option><option value="true">Somente ativos</option><option value="false">Somente inativos</option></select></label>
      <label>Ordenação<select value={filters.sortOrder} onChange={(event) => filter({ ...filters, sortOrder: event.target.value as "asc" | "desc" })}><option value="desc">Mais recentes</option><option value="asc">Mais antigos</option></select></label>
    </div>
    {notice ? <output className="user-success">{notice}</output> : null}
    {edit.error ? <AlertBanner>{userError(edit.error)}</AlertBanner> : null}
    {list.status === "loading" ? <output className="user-list-message">Carregando usuários…</output> : null}
    {list.status === "error" ? <div><AlertBanner>{userError(list.error)}</AlertBanner><button type="button" className="btn-secondary" onClick={() => void list.refetch()}>Tentar novamente</button></div> : null}
    {list.status === "success" && list.items.length === 0 ? <p className="user-list-message">Nenhum usuário encontrado com estes filtros.</p> : null}
    {list.status === "success" && list.items.length > 0 ? <>
      <p className="user-muted">Exibindo {list.items.length} de {list.total} usuários.</p>
      <ul className="user-list" aria-label="Contas de usuários">{list.items.map((account) => <li className="user-row" key={account.id}>
        <div className="user-row-identity"><h3>{account.name}{account.id === user.id ? <span className="user-own">Sua conta</span> : null}</h3><p>{account.email}</p></div>
        <div className="user-row-access"><span>{account.customProfileName ?? ROLE_LABELS[account.role]}</span><StatusPill tone={account.active ? "good" : "neutral"}>{account.active ? "Ativo" : "Inativo"}</StatusPill></div>
        <p className="user-row-link">{account.driverId ? account.driverName ?? "Motorista vinculado" : "Sem vínculo de motorista"}</p>
        <button type="button" className="btn-secondary" disabled={edit.loadingId !== null} aria-label={`Editar ${account.name}`} onClick={() => { setNotice(""); void edit.open(account.id); }}>{edit.loadingId === account.id ? "Abrindo…" : "Editar conta"}</button>
      </li>)}</ul>
      <Pagination page={list.page} totalPages={list.totalPages} onChange={list.goToPage} label="usuários" />
    </> : null}
    {creating || edit.target ? <UserEditor key={edit.target?.id ?? "new"} account={edit.target ?? undefined} ownId={user.id} onClose={close} onSaved={saved} /> : null}
  </div>;
}
