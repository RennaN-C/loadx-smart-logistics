import { useState } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { listProfiles, type AccessProfile } from "../api/profilesApi";
import { ProfileEditor } from "./ProfileEditor";
import "../../users/components/UserManagement.css";
import "./ProfilesPanel.css";

export function ProfilesPanel() {
  const { user } = useAuth();
  const allowed = user?.active && user.role === "ADMIN";
  const list = useResourceList(listProfiles, allowed);
  const [editing, setEditing] = useState<AccessProfile | "new" | null>(null);
  const [notice, setNotice] = useState("");
  if (!allowed) return null;
  return <div className="user-management profile-management">
    <div className="user-toolbar"><p className="user-muted">Defina o acesso à operação. Identidade, segurança e configurações administrativas permanecem protegidas.</p><button type="button" className="btn-primary" onClick={() => { setNotice(""); setEditing("new"); }}>Criar perfil</button></div>
    {notice ? <output className="user-success">{notice}</output> : null}
    {list.status === "loading" ? <output>Carregando perfis…</output> : null}
    {list.status === "error" ? <div><AlertBanner>Não foi possível consultar os perfis.</AlertBanner><button className="btn-secondary" type="button" onClick={() => void list.refetch()}>Tentar novamente</button></div> : null}
    {list.status === "success" && !list.items.length ? <p>Nenhum perfil nesta página.</p> : null}
    {list.status === "success" ? <ul className="user-list" aria-label="Perfis de acesso">{list.items.map((profile) => <li className="profile-row" key={profile.id}><div><h3>{profile.name}</h3><p>{profile.description || "Sem descrição adicional"}</p><span className="user-muted">{profile.permissions.length} permissões · {profile.user_count} usuário(s){profile.system_role ? " · Sistema protegido" : " · Personalizado"}</span></div><StatusPill tone={profile.active ? "good" : "neutral"}>{profile.active ? "Ativo" : "Inativo"}</StatusPill>{profile.system_role ? <details><summary>Consultar permissões</summary><ul className="profile-code-list">{profile.permissions.map((code) => <li key={code}>{code}</li>)}</ul></details> : <button className="btn-secondary" type="button" onClick={() => setEditing(profile)} aria-label={`Editar ${profile.name}`}>Editar perfil</button>}</li>)}</ul> : null}
    <Pagination page={list.page} totalPages={list.totalPages} onChange={list.goToPage} label="perfis" />
    {editing ? <ProfileEditor profile={editing === "new" ? undefined : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); setNotice("Perfil salvo com sucesso."); void list.refetch(); }} /> : null}
  </div>;
}
