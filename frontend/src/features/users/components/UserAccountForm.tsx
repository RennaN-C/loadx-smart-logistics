import { ProfileAccessSummary } from "../../access-profiles/components/ProfileAccessSummary";
import { ProfileAssignment } from "../../access-profiles/components/ProfileAssignment";
import type { FormEvent } from "react";
import { FormField } from "../../../components/FormField";
import type { Role } from "../../auth/types";
import type { UserAccount, UserInput } from "../api/usersApi";
import { DriverLinkField } from "./DriverLinkField";
import { ROLE_LABELS, type PasswordDraft } from "./userPresentation";

interface Props {
  readonly onManageProfiles?: () => void;
  readonly account?: UserAccount;
  readonly draft: UserInput;
  readonly onDraft: (draft: UserInput) => void;
  readonly security: PasswordDraft;
  readonly onSecurity: (draft: PasswordDraft) => void;
  readonly saving: boolean;
  readonly canSave: boolean;
  readonly onSubmit: (event: FormEvent) => void;
  readonly onClose: () => void;
}
export function UserAccountForm({ account, draft, onDraft, security, onSecurity, saving, canSave, onSubmit, onClose, onManageProfiles }: Props) {
  return <form className="user-account-form" aria-label={account ? "Editar conta" : "Criar usuário"} aria-busy={saving} onSubmit={onSubmit}>
    <fieldset className="user-form-group" disabled={saving}><legend>Identificação da conta</legend><div className="user-form-grid">
      <FormField id="user-name" label="Nome"><input id="user-name" value={draft.name} required maxLength={120} autoComplete="off" onChange={(event) => onDraft({ ...draft, name: event.target.value })} /></FormField>
      <FormField id="user-email" label="E-mail"><input id="user-email" type="email" value={draft.email} required maxLength={255} autoComplete="off" onChange={(event) => onDraft({ ...draft, email: event.target.value })} /></FormField>
      <FormField id="user-active" label="Estado da conta"><select id="user-active" value={String(draft.active)} onChange={(event) => onDraft({ ...draft, active: event.target.value === "true" })}><option value="true">Ativo</option><option value="false">Inativo</option></select></FormField>
    </div></fieldset>
    <fieldset className="user-form-group user-access-section" disabled={saving}><legend>Acesso e permissões</legend>
      <div className="access-type-options">
        <label><input type="radio" name="access-type" checked={draft.role !== "CUSTOM"} onChange={() => onDraft({ ...draft, role: "CHECKER", customProfileId: null, driverId: null })} /><span>Perfil padrão do sistema<small>Funções protegidas do LoadX</small></span></label>
        <label><input type="radio" name="access-type" checked={draft.role === "CUSTOM"} onChange={() => onDraft({ ...draft, role: "CUSTOM", customProfileId: null, driverId: null })} /><span>Perfil personalizado<small>Acesso reutilizável por módulo</small></span></label>
      </div>
      {draft.role !== "CUSTOM" ? <div className="user-form-grid">
        <FormField id="user-role" label="Perfil de acesso"><select id="user-role" value={draft.role} onChange={(event) => { const role = event.target.value as Role; onDraft({ ...draft, role, driverId: role === "DRIVER" ? draft.driverId : null, customProfileId: role === "CUSTOM" ? draft.customProfileId : null }); }}>{Object.entries(ROLE_LABELS).filter(([role]) => role !== "CUSTOM").map(([role, label]) => <option value={role} key={role}>{label}</option>)}</select></FormField>
      </div> : <ProfileAssignment value={draft.customProfileId ?? null} onChange={(customProfileId) => onDraft({ ...draft, customProfileId })} disabled={saving} />}
      <ProfileAccessSummary key={`${draft.role}:${draft.customProfileId ?? ""}`} role={draft.role} profileId={draft.customProfileId ?? null} />
      {draft.role === "DRIVER" ? <DriverLinkField value={draft.driverId} onChange={(driverId) => onDraft({ ...draft, driverId })} disabled={saving} /> : null}
      <p className="user-muted">O perfil define as ações autorizadas. Consulta e gestão são independentes; mudanças de acesso encerram as sessões da conta.</p>
      {onManageProfiles ? <button type="button" className="access-manage-link" onClick={onManageProfiles}>Gerenciar perfis de acesso →</button> : null}
    </fieldset>
    <fieldset className="user-form-group" disabled={saving}><legend>Segurança</legend>
      {account ? <label className="user-checkbox"><input type="checkbox" checked={security.enabled} onChange={(event) => onSecurity({ enabled: event.target.checked, password: "", confirmation: "" })} />Redefinir senha administrativamente</label> : null}
      {security.enabled ? <><p className="user-muted">Use de 15 a 128 caracteres; senhas comuns são recusadas. A senha não será exibida após salvar. Nenhum e-mail é enviado por esta operação.</p><div className="user-form-grid">
        <FormField id="user-password" label={account ? "Nova senha" : "Senha inicial"}><input id="user-password" type="password" autoComplete="new-password" value={security.password} required maxLength={128} onChange={(event) => onSecurity({ ...security, password: event.target.value })} /></FormField>
        <FormField id="user-password-confirm" label="Confirmar senha"><input id="user-password-confirm" type="password" autoComplete="new-password" value={security.confirmation} required maxLength={128} onChange={(event) => onSecurity({ ...security, confirmation: event.target.value })} /></FormField>
      </div></> : <p className="user-muted">A senha atual permanece protegida. Ative a opção acima somente para definir uma nova senha.</p>}
    </fieldset>
    <div className="user-actions"><button className="btn-primary" disabled={saving || !canSave} type="submit">{saving ? "Salvando…" : "Salvar usuário"}</button><button className="btn-secondary" disabled={saving} type="button" onClick={onClose}>Cancelar</button></div>
  </form>;
}
