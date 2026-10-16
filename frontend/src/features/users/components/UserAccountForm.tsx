import { ProfileAssignment } from "../../access-profiles/components/ProfileAssignment";
import type { FormEvent } from "react";
import { FormField } from "../../../components/FormField";
import type { Role } from "../../auth/types";
import type { UserAccount, UserInput } from "../api/usersApi";
import { DriverLinkField } from "./DriverLinkField";
import { ROLE_LABELS, type PasswordDraft } from "./userPresentation";

interface Props {
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
export function UserAccountForm({ account, draft, onDraft, security, onSecurity, saving, canSave, onSubmit, onClose }: Props) {
  return <form className="user-account-form" aria-label={account ? "Editar conta" : "Criar usuário"} aria-busy={saving} onSubmit={onSubmit}>
    <fieldset className="user-form-group" disabled={saving}><legend>Identificação da conta</legend><div className="user-form-grid">
      <FormField id="user-name" label="Nome"><input id="user-name" value={draft.name} required maxLength={120} autoComplete="off" onChange={(event) => onDraft({ ...draft, name: event.target.value })} /></FormField>
      <FormField id="user-email" label="E-mail"><input id="user-email" type="email" value={draft.email} required maxLength={255} autoComplete="off" onChange={(event) => onDraft({ ...draft, email: event.target.value })} /></FormField>
      <FormField id="user-role" label="Perfil de acesso"><select id="user-role" value={draft.role} onChange={(event) => { const role = event.target.value as Role; onDraft({ ...draft, role, driverId: role === "DRIVER" ? draft.driverId : null, customProfileId: role === "CUSTOM" ? draft.customProfileId : null }); }}>{Object.entries(ROLE_LABELS).map(([role, label]) => <option value={role} key={role}>{label}</option>)}</select></FormField>
      <FormField id="user-active" label="Estado da conta"><select id="user-active" value={String(draft.active)} onChange={(event) => onDraft({ ...draft, active: event.target.value === "true" })}><option value="true">Ativo</option><option value="false">Inativo</option></select></FormField>
    </div><p className="user-muted">Mudar o perfil para outro tipo remove o vínculo de motorista. O último administrador ativo é protegido pelo servidor.</p></fieldset>
    {draft.role === "CUSTOM" ? <ProfileAssignment value={draft.customProfileId ?? null} onChange={(customProfileId) => onDraft({ ...draft, customProfileId })} disabled={saving} /> : null}
    {draft.role === "DRIVER" ? <DriverLinkField value={draft.driverId} onChange={(driverId) => onDraft({ ...draft, driverId })} disabled={saving} /> : null}
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
