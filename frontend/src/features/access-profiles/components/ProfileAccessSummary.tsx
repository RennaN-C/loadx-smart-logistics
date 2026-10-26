import { useEffect, useState } from "react";
import { getProfile, listProfiles, type AccessProfile } from "../api/profilesApi";
import type { Role } from "../../auth/types";
import { PermissionDetails } from "./PermissionDetails";
import { MODULE_LABELS, permissionGroups } from "./profilePresentation";
import { usePermissionCatalog } from "./usePermissionCatalog";
import "./ProfilesPanel.css";

export function ProfileAccessSummary({ role, profileId }: { readonly role: Role; readonly profileId: string | null }) {
  const catalog = usePermissionCatalog();
  const [profile, setProfile] = useState<AccessProfile | null>(null);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let current = true;
    setProfile(null); setStatus("loading");
    if (role === "CUSTOM" && !profileId) { setStatus("success"); return; }
    const request = role === "CUSTOM" ? getProfile(profileId!) : listProfiles({ page: 1, pageSize: 4 }).then((page) => page.items.find((item) => item.system_role === role) ?? null);
    request.then((value) => { if (current) { setProfile(value); setStatus(value ? "success" : "error"); } }).catch(() => { if (current) setStatus("error"); });
    return () => { current = false; };
  }, [role, profileId, attempt]);
  if (role === "CUSTOM" && !profileId) return <p className="user-muted">Selecione um perfil para consultar o acesso que será atribuído.</p>;
  if (status === "error" || catalog.status === "error") return <div className="access-summary" role="alert"><p>Não foi possível consultar o resumo de acesso.</p><button className="btn-secondary" type="button" onClick={() => { setAttempt((value) => value + 1); catalog.retry(); }}>Consultar novamente</button></div>;
  if (status === "loading" || catalog.status === "loading" || !profile) return <output className="user-muted">Consultando acesso do perfil…</output>;
  const modules = permissionGroups(catalog.items.filter((item) => profile.permissions.includes(item.code)));
  return <section className="access-summary" aria-label="Resumo de acesso selecionado">
    <div className="access-summary-heading"><strong>{profile.name}</strong><span>{profile.active ? "Ativo" : "Inativo"} · {profile.permissions.length} permissões</span></div>
    <p>{profile.description || "Perfil personalizado da operação."}</p>
    <p className="user-muted">{modules.length} módulos disponíveis</p>
    <div className="access-module-tags">{modules.slice(0, 5).map(([module]) => <span key={module}>{MODULE_LABELS[module] ?? "Outras ações"}</span>)}{modules.length > 5 ? <span>+{modules.length - 5} módulos</span> : null}</div>
    <PermissionDetails permissions={profile.permissions} catalog={catalog.items} />
    {role === "DRIVER" ? <p className="user-muted">O acesso operacional exige vínculo ativo e se limita às viagens e entregas próprias.</p> : null}
    {role === "CHECKER" ? <p className="user-muted">A consulta de planejamento mantém o limite a planos aprovados.</p> : null}
  </section>;
}
