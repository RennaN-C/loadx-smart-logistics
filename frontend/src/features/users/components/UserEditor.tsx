import { useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { Modal } from "../../../components/Modal";
import type { Role } from "../../auth/types";
import { createUser, updateUser, type UserAccount, type UserInput } from "../api/usersApi";
import { DriverLinkField } from "./DriverLinkField";
import { accountChanges, revokesSessions, ROLE_LABELS, userError } from "./userPresentation";

interface Props { readonly account?: UserAccount; readonly ownId: string; readonly onClose: () => void; readonly onSaved: (account: UserAccount, revoked: boolean) => void }
export function UserEditor({ account, ownId, onClose, onSaved }: Props) {
  const [draft, setDraft] = useState<UserInput>({ name: account?.name ?? "", email: account?.email ?? "", role: account?.role ?? "CHECKER", active: account?.active ?? true, driverId: account?.driverId ?? null });
  const [password, setPassword] = useState(""); const [confirm, setConfirm] = useState("");
  const [resetPassword, setResetPassword] = useState(!account);
  const [confirming, setConfirming] = useState(false); const [saving, setSaving] = useState(false); const [error, setError] = useState<string | null>(null);
  const normalized = { ...draft, name: draft.name.trim(), email: draft.email.trim().toLowerCase() };
  const changes = accountChanges(account, normalized, resetPassword ? password : undefined);
  const sensitive = revokesSessions(changes) || changes.active !== undefined;
  function submit(event: FormEvent) {
    event.preventDefault(); if (saving) return; setError(null);
    if (!normalized.name) { setError("Informe o nome da pessoa."); return; }
    if (resetPassword && (Array.from(password.normalize("NFC")).length < 15 || Array.from(password.normalize("NFC")).length > 128)) { setError("A senha deve ter de 15 a 128 caracteres."); return; }
    if (resetPassword && password !== confirm) { setError("A confirmação deve ser igual à senha informada."); return; }
    if (account && sensitive) { setConfirming(true); return; }
    void save();
  }
  async function save() {
    if (saving) return; setSaving(true); setError(null);
    try {
      const saved = account ? await updateUser(account.id, changes) : await createUser({ ...normalized, password });
      setPassword(""); setConfirm(""); onSaved(saved, revokesSessions(changes));
    } catch (caught) { setError(userError(caught)); setConfirming(false); setPassword(""); setConfirm(""); }
    finally { setSaving(false); }
  }
  return <Modal title={account ? "Editar conta" : "Criar usuário"} subtitle="Administração de identidade do LoadX standalone" onClose={() => { if (!saving) onClose(); }}>
    <div className="user-editor">
      {error ? <AlertBanner>{error}</AlertBanner> : null}
      {confirming ? <section aria-labelledby="user-confirm-title" className="user-confirmation">
        <h3 id="user-confirm-title">Confirmar alterações sensíveis</h3>
        <p>Confira as alterações na conta de <strong>{account?.name}</strong> antes de continuar.</p>
        <dl><div><dt>Perfil</dt><dd>{ROLE_LABELS[draft.role]}</dd></div><div><dt>Estado</dt><dd>{draft.active ? "Ativo" : "Inativo"}</dd></div><div><dt>Vínculo</dt><dd>{draft.driverId ? "Motorista vinculado" : "Sem vínculo de motorista"}</dd></div><div><dt>Senha</dt><dd>{resetPassword ? "Será redefinida" : "Preservada"}</dd></div></dl>
        {revokesSessions(changes) ? <p>As sessões desta conta serão encerradas.{account?.id === ownId ? " Esta é sua conta: será necessário entrar novamente." : ""}</p> : null}
        <div className="user-actions"><button className="btn-primary" type="button" disabled={saving} onClick={() => void save()}>{saving ? "Salvando…" : "Confirmar alterações"}</button><button className="btn-secondary" type="button" disabled={saving} onClick={() => setConfirming(false)}>Voltar ao formulário</button></div>
      </section> : <form className="user-account-form" aria-label={account ? "Editar conta" : "Criar usuário"} aria-busy={saving} onSubmit={submit}>
        <fieldset className="user-form-group" disabled={saving}><legend>Identificação da conta</legend><div className="user-form-grid">
          <FormField id="user-name" label="Nome"><input id="user-name" value={draft.name} required maxLength={120} autoComplete="off" onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></FormField>
          <FormField id="user-email" label="E-mail"><input id="user-email" type="email" value={draft.email} required maxLength={255} autoComplete="off" onChange={(event) => setDraft({ ...draft, email: event.target.value })} /></FormField>
          <FormField id="user-role" label="Perfil de acesso"><select id="user-role" value={draft.role} onChange={(event) => { const role = event.target.value as Role; setDraft({ ...draft, role, driverId: role === "DRIVER" ? draft.driverId : null }); }}>{Object.entries(ROLE_LABELS).map(([role, label]) => <option value={role} key={role}>{label}</option>)}</select></FormField>
          <FormField id="user-active" label="Estado da conta"><select id="user-active" value={String(draft.active)} onChange={(event) => setDraft({ ...draft, active: event.target.value === "true" })}><option value="true">Ativo</option><option value="false">Inativo</option></select></FormField>
        </div><p className="user-muted">Mudar o perfil para outro tipo remove o vínculo de motorista. O último administrador ativo é protegido pelo servidor.</p></fieldset>
        {draft.role === "DRIVER" ? <DriverLinkField value={draft.driverId} onChange={(driverId) => setDraft({ ...draft, driverId })} disabled={saving} /> : null}
        <fieldset className="user-form-group" disabled={saving}><legend>Segurança</legend>
          {account ? <label className="user-checkbox"><input type="checkbox" checked={resetPassword} onChange={(event) => { setResetPassword(event.target.checked); setPassword(""); setConfirm(""); }} />Redefinir senha administrativamente</label> : null}
          {resetPassword ? <><p className="user-muted">Use de 15 a 128 caracteres; senhas comuns são recusadas. A senha não será exibida após salvar. Nenhum e-mail é enviado por esta operação.</p><div className="user-form-grid">
            <FormField id="user-password" label={account ? "Nova senha" : "Senha inicial"}><input id="user-password" type="password" autoComplete="new-password" value={password} required maxLength={128} onChange={(event) => setPassword(event.target.value)} /></FormField>
            <FormField id="user-password-confirm" label="Confirmar senha"><input id="user-password-confirm" type="password" autoComplete="new-password" value={confirm} required maxLength={128} onChange={(event) => setConfirm(event.target.value)} /></FormField>
          </div></> : <p className="user-muted">A senha atual permanece protegida. Ative a opção acima somente para definir uma nova senha.</p>}
        </fieldset>
        <div className="user-actions"><button className="btn-primary" disabled={saving || (Boolean(account) && Object.keys(changes).length === 0)} type="submit">{saving ? "Salvando…" : "Salvar usuário"}</button><button className="btn-secondary" disabled={saving} type="button" onClick={onClose}>Cancelar</button></div>
      </form>}
    </div>
  </Modal>;
}
