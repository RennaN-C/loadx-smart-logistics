import type { Dispatch, FormEvent, SetStateAction } from "react";
import { PermissionDetails } from "./PermissionDetails";
import { MODULE_LABELS, permissionGroups } from "./profilePresentation";
import type { PermissionDefinition, ProfileInput } from "../api/profilesApi";

interface Props {
  readonly draft: ProfileInput;
  readonly onDraft: Dispatch<SetStateAction<ProfileInput>>;
  readonly catalog: PermissionDefinition[];
  readonly saving: boolean;
  readonly userCount: number;
  readonly onSubmit: (event: FormEvent) => void;
  readonly onClose: () => void;
}
export function ProfileForm({ draft, onDraft, catalog, saving, userCount, onSubmit, onClose }: Props) {
  function toggle(code: string) { onDraft((value) => ({ ...value, permissions: value.permissions.includes(code) ? value.permissions.filter((item) => item !== code) : [...value.permissions, code] })); }
  return <form className="profile-editor-form" aria-label="Dados do perfil" onSubmit={onSubmit}>
    <fieldset className="user-form-group" disabled={saving}><legend>Identificação</legend><div className="user-form-grid">
      <label htmlFor="profile-name">Nome do perfil<input id="profile-name" required maxLength={120} value={draft.name} onChange={(event) => onDraft({ ...draft, name: event.target.value })} /></label>
      <label htmlFor="profile-state">Estado<select id="profile-state" value={String(draft.active)} onChange={(event) => onDraft({ ...draft, active: event.target.value === "true" })}><option value="true">Ativo</option><option value="false" disabled={userCount > 0}>Inativo</option></select></label>
    </div><label htmlFor="profile-description">Descrição<textarea id="profile-description" maxLength={500} value={draft.description} onChange={(event) => onDraft({ ...draft, description: event.target.value })} /></label>
    {userCount > 0 ? <p className="user-muted">{userCount === 1 ? "1 usuário associado." : `${userCount} usuários associados.`} Remova {userCount === 1 ? "a associação" : "as associações"} antes de desativar.</p> : null}</fieldset>
    <div className="profile-permissions-head"><h3>Permissões por módulo</h3><output>{draft.permissions.length === 1 ? "1 selecionada" : `${draft.permissions.length} selecionadas`}</output></div>
    <p className="user-muted">Selecione somente as ações necessárias. Gestão não concede consulta automaticamente; inclua ambas para um fluxo completo.</p>
    {draft.permissions.length ? <PermissionDetails permissions={draft.permissions} catalog={catalog} /> : null}
    <PermissionGroups catalog={catalog.filter((item) => item.delegable)} selected={draft.permissions} saving={saving} onToggle={toggle} />
    <details className="profile-reserved"><summary>Permissões protegidas pelo sistema</summary><p className="user-muted">Estas ações são consultáveis e não podem ser atribuídas a perfis personalizados.</p><PermissionGroups catalog={catalog.filter((item) => !item.delegable)} selected={draft.permissions} saving={saving} onToggle={toggle} /></details>
    <div className="user-actions"><button className="btn-primary" type="submit" disabled={saving}>Revisar e salvar</button><button className="btn-secondary" type="button" disabled={saving} onClick={onClose}>Cancelar</button></div>
  </form>;
}
function permissionNote(item: PermissionDefinition) {
  if (item.classification === "identity") return "Exige identidade e vínculo próprio; não delegável";
  if (!item.delegable) return "Protegida pelo sistema; não delegável";
  if (item.classification === "operational") return "Exige operador autenticado; preserva as regras de conferência";
  return "Delegável neste perfil";
}
function PermissionGroups({ catalog, selected, saving, onToggle }: { readonly catalog: PermissionDefinition[]; readonly selected: string[]; readonly saving: boolean; readonly onToggle: (code: string) => void }) {
  return <div className="profile-permissions">{permissionGroups(catalog).map(([module, items]) => <details key={module} className="profile-permission-module"><summary><span>{MODULE_LABELS[module] ?? "Outras ações"}</span><span>{items.filter((item) => selected.includes(item.code)).length} / {items.length}</span></summary><fieldset className="profile-permission-group" aria-label={MODULE_LABELS[module] ?? "Outras ações"}>{items.map((item) => <label htmlFor={`permission-${item.code}`} key={item.code} className="profile-permission-option"><input id={`permission-${item.code}`} type="checkbox" aria-label={item.label} disabled={!item.delegable || saving} checked={selected.includes(item.code)} onChange={() => onToggle(item.code)} /><span><strong>{item.label}</strong><small>{permissionNote(item)}</small></span></label>)}</fieldset></details>)}</div>;
}
