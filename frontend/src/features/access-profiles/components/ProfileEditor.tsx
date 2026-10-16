import { useEffect, useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { permissionCatalog, saveProfile, type AccessProfile, type PermissionDefinition, type ProfileInput } from "../api/profilesApi";
import { profileError } from "./profilePresentation";

export function ProfileEditor({ profile, onClose, onSaved }: { readonly profile?: AccessProfile; readonly onClose: () => void; readonly onSaved: () => void }) {
  const [draft, setDraft] = useState<ProfileInput>({ name: profile?.name ?? "", description: profile?.description ?? "", active: profile?.active ?? true, permissions: profile?.permissions ?? [] });
  const [catalog, setCatalog] = useState<PermissionDefinition[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { let current = true; setFailed(false); permissionCatalog().then((items) => { if (current) setCatalog(items); }).catch(() => { if (current) setFailed(true); }); return () => { current = false; }; }, [attempt]);
  useEffect(() => { document.getElementById(confirm ? "profile-confirm" : "profile-name")?.focus(); }, [confirm, catalog]);
  const groups = new Map<string, PermissionDefinition[]>();
  for (const item of catalog ?? []) groups.set(item.module, [...(groups.get(item.module) ?? []), item]);
  function toggle(code: string) { setDraft((value) => ({ ...value, permissions: value.permissions.includes(code) ? value.permissions.filter((item) => item !== code) : [...value.permissions, code] })); }
  function submit(event: FormEvent) { event.preventDefault(); if (!saving && draft.name.trim()) setConfirm(true); }
  async function save() {
    if (saving) return;
    setSaving(true); setError(null);
    try { await saveProfile({ ...draft, name: draft.name.trim(), permissions: [...draft.permissions].sort() }, profile); onSaved(); }
    catch (error_) { setError(profileError(error_)); setConfirm(false); }
    finally { setSaving(false); }
  }
  return <Modal title={profile ? "Editar perfil" : "Criar perfil personalizado"} subtitle="Permissões locais do LoadX" onClose={() => { if (!saving) onClose(); }}>
    {error ? <AlertBanner>{error}</AlertBanner> : null}
    {failed ? <div><AlertBanner>Não foi possível consultar o catálogo de permissões.</AlertBanner><button className="btn-secondary" type="button" onClick={() => setAttempt((value) => value + 1)}>Tentar novamente</button></div> : null}
    {!catalog && !failed ? <output>Consultando permissões…</output> : null}
    {catalog && confirm ? <section aria-label="Confirmar perfil"><h3>Confirmar permissões</h3><p>O perfil <strong>{draft.name}</strong> terá {draft.permissions.length} permissões e ficará {draft.active ? "ativo" : "inativo"}.</p><p>Alterações de permissão encerram as sessões dos usuários associados. Permissões de leitura e gestão são independentes.</p><div className="user-actions"><button id="profile-confirm" className="btn-primary" type="button" disabled={saving} onClick={() => void save()}>{saving ? "Salvando…" : "Confirmar perfil"}</button><button className="btn-secondary" type="button" disabled={saving} onClick={() => setConfirm(false)}>Revisar permissões</button></div></section> : null}
    {catalog && !confirm ? <form aria-label="Dados do perfil" onSubmit={submit}>
      <fieldset className="user-form-group" disabled={saving}><legend>Identificação</legend><div className="user-form-grid">
        <label htmlFor="profile-name">Nome do perfil<input id="profile-name" required maxLength={120} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
        <label htmlFor="profile-state">Estado<select id="profile-state" value={String(draft.active)} onChange={(event) => setDraft({ ...draft, active: event.target.value === "true" })}><option value="true">Ativo</option><option value="false" disabled={Boolean(profile?.user_count)}>Inativo</option></select></label>
      </div><label htmlFor="profile-description">Descrição<textarea id="profile-description" maxLength={500} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
      {profile?.user_count ? <p className="user-muted">{profile.user_count} usuário(s) associado(s). Remova as associações antes de desativar.</p> : null}</fieldset>
      <div className="profile-permissions-head"><h3>Permissões por módulo</h3><output>{draft.permissions.length} selecionadas</output></div>
      <p className="user-muted">Selecione somente as ações necessárias. Gestão não concede consulta automaticamente; inclua ambas para um fluxo completo.</p>
      <div className="profile-permissions">{[...groups].map(([module, items]) => <fieldset key={module} className="profile-permission-group"><legend>{MODULE_LABELS[module] ?? module}</legend>{items.map((item) => <label key={item.code} className="profile-permission-option"><input type="checkbox" disabled={!item.delegable || saving} checked={draft.permissions.includes(item.code)} onChange={() => toggle(item.code)} /><span><strong>{item.label}</strong><small>{item.delegable ? item.classification === "operational" ? "Ação registrada com a identidade real do operador" : "Delegável neste perfil" : item.classification === "identity" ? "Exige identidade e vínculo próprio; não delegável" : "Protegida pelo sistema; não delegável"}</small></span></label>)}</fieldset>)}</div>
      <div className="user-actions"><button className="btn-primary" type="submit" disabled={saving}>Revisar e salvar</button><button className="btn-secondary" type="button" disabled={saving} onClick={onClose}>Cancelar</button></div>
    </form> : null}
  </Modal>;
}
const MODULE_LABELS: Record<string, string> = { customers: "Clientes", products: "Produtos", trucks: "Caminhões", drivers: "Motoristas", orders: "Pedidos", planning: "Planejamento", loading: "Carregamento", trips: "Viagens", deliveries: "Entregas", occurrences: "Ocorrências", reports: "Relatórios", messages: "Comunicação", audit: "Auditoria", users: "Usuários", profiles: "Perfis", settings: "Configurações", integrations: "Integrações", imports: "Importações" };
