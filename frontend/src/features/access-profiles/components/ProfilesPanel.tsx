import { useState } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { Modal } from "../../../components/Modal";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { listProfiles, type AccessProfile, type PermissionDefinition } from "../api/profilesApi";
import { PermissionDetails } from "./PermissionDetails";
import { usePermissionCatalog } from "./usePermissionCatalog";
import { ProfileEditor } from "./ProfileEditor";
import "../../users/components/UserManagement.css";
import "./ProfilesPanel.css";

export function ProfilesPanel({ active = true }: { readonly active?: boolean }) {
  const { user } = useAuth();
  const allowed = Boolean(user?.active && user.role === "ADMIN");
  const list = useResourceList(listProfiles, allowed && active);
  const catalog = usePermissionCatalog(Boolean(allowed && active));
  const [editing, setEditing] = useState<AccessProfile | "new" | null>(null);
  const [viewing, setViewing] = useState<AccessProfile | null>(null);
  const [notice, setNotice] = useState("");
  if (!allowed) return null;
  return <div className="user-management profile-management">
    <div className="user-toolbar"><p className="user-muted">Crie acessos reutilizáveis para a equipe. Os quatro perfis do sistema permanecem protegidos.</p><button type="button" className="btn-primary" onClick={() => { setNotice(""); setEditing("new"); }}>Criar perfil</button></div>
    {notice ? <output className="user-success">{notice}</output> : null}
    {list.status === "loading" ? <output>Carregando perfis…</output> : null}
    {list.status === "error" ? <div><AlertBanner>Não foi possível consultar os perfis.</AlertBanner><button className="btn-secondary" type="button" onClick={() => void list.refetch()}>Tentar novamente</button></div> : null}
    {list.status === "success" && !list.items.length ? <p>Nenhum perfil nesta página.</p> : null}
    {list.status === "success" ? <ProfileRows items={list.items} catalogReady={catalog.status === "success"} onView={setViewing} onEdit={setEditing} /> : null}
    {catalog.status === "error" ? <div className="access-catalog-error" role="alert">Não foi possível consultar os nomes das permissões. <button className="btn-secondary" type="button" onClick={catalog.retry}>Consultar catálogo novamente</button></div> : null}
    {catalog.status === "loading" ? <output className="user-muted">Consultando catálogo de ações…</output> : null}
    <Pagination page={list.page} totalPages={list.totalPages} onChange={list.goToPage} label="perfis" />
    {viewing && active ? <ProfileInspector profile={viewing} catalog={catalog.items} onClose={() => setViewing(null)} /> : null}
    {editing ? <ProfileEditor active={active} profile={editing === "new" ? undefined : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); setNotice("Perfil salvo com sucesso."); void list.refetch(); }} /> : null}
  </div>;
}

function ProfileRows({ items, catalogReady, onView, onEdit }: { readonly items: AccessProfile[]; readonly catalogReady: boolean; readonly onView: (profile: AccessProfile) => void; readonly onEdit: (profile: AccessProfile) => void }) {
  return <ul className="access-profile-list" aria-label="Perfis de acesso">{items.map((profile) => <li className="access-profile-row" key={profile.id}>
      <div className="access-profile-identity"><div className="access-profile-title"><h3>{profile.name}</h3><span className="access-profile-kind">{profile.system_role ? "Protegido" : "Personalizado"}</span></div><p>{profile.description || "Sem descrição adicional"}</p></div>
      <div className="access-profile-meta"><span>{profile.permissions.length} permissões</span><span>{profile.user_count} usuário(s)</span><StatusPill tone={profile.active ? "good" : "neutral"}>{profile.active ? "Ativo" : "Inativo"}</StatusPill></div>
      <div className="access-profile-actions"><button type="button" className="access-view-button" disabled={!catalogReady} onClick={() => onView(profile)} aria-label={`Ver permissões de ${profile.name}`}>Ver permissões</button>{profile.system_role ? <span className="user-muted">Somente consulta</span> : <button className="btn-secondary" type="button" onClick={() => onEdit(profile)} aria-label={`Editar ${profile.name}`}>Editar perfil</button>}</div>
    </li>)}</ul>;
}

function ProfileInspector({ profile, catalog, onClose }: { readonly profile: AccessProfile; readonly catalog: PermissionDefinition[]; readonly onClose: () => void }) {
  return <Modal title={profile.name} subtitle={profile.description || "Permissões do perfil"} onClose={onClose}><p className="user-muted">{profile.active ? "Ativo" : "Inativo"} · {profile.permissions.length} permissões · {profile.user_count} usuário(s) · {profile.system_role ? "Perfil protegido do sistema" : "Perfil personalizado"}</p><PermissionDetails expanded permissions={profile.permissions} catalog={catalog} /><div className="user-actions"><button type="button" className="btn-secondary" onClick={onClose}>Fechar consulta</button></div></Modal>;
}
