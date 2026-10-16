import { useEffect, useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { createUser, updateUser, type UserAccount, type UserInput } from "../api/usersApi";
import { UserAccountForm } from "./UserAccountForm";
import { UserChangeConfirmation } from "./UserChangeConfirmation";
import { accountChanges, revokesSessions, userError, validateDraft, type PasswordDraft } from "./userPresentation";

interface Props { readonly account?: UserAccount; readonly ownId: string; readonly onClose: () => void; readonly onSaved: (account: UserAccount, revoked: boolean) => void }
export function UserEditor({ account, ownId, onClose, onSaved }: Props) {
  const [draft, setDraft] = useState<UserInput>({ name: account?.name ?? "", email: account?.email ?? "", role: account?.role ?? "CHECKER", active: account?.active ?? true, customProfileId: account?.customProfileId ?? null, driverId: account?.driverId ?? null });
  const [security, setSecurity] = useState<PasswordDraft>({ enabled: !account, password: "", confirmation: "" });
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const normalized = { ...draft, name: draft.name.trim(), email: draft.email.trim().toLowerCase() };
  const changes = accountChanges(account, normalized, security.enabled ? security.password : undefined);
  const revoking = revokesSessions(changes);
  useEffect(() => {
    document.getElementById(confirming ? "user-confirm-action" : "user-name")?.focus();
  }, [confirming]);
  function submit(event: FormEvent) {
    event.preventDefault();
    if (saving) { return; }
    const validation = validateDraft(normalized, security);
    setError(validation);
    if (validation) { return; }
    if (account && (revoking || changes.active !== undefined)) { setConfirming(true); return; }
    void save();
  }
  function clearPasswords() { setSecurity((current) => ({ ...current, password: "", confirmation: "" })); }
  async function save() {
    if (saving) { return; }
    setSaving(true);
    setError(null);
    try {
      const saved = account ? await updateUser(account.id, changes) : await createUser({ ...normalized, password: security.password });
      clearPasswords();
      onSaved(saved, revoking);
    } catch (error_) {
      setError(userError(error_));
      setConfirming(false);
      clearPasswords();
    } finally { setSaving(false); }
  }
  return <Modal title={account ? "Editar conta" : "Criar usuário"} subtitle="Administração de identidade do LoadX standalone" onClose={() => { if (!saving) onClose(); }}>
    <div className="user-editor">
      {error ? <AlertBanner>{error}</AlertBanner> : null}
      {confirming ? <UserChangeConfirmation name={account?.name ?? draft.name} draft={draft} passwordChanged={security.enabled} revoking={revoking} ownAccount={account?.id === ownId} saving={saving} onConfirm={() => void save()} onBack={() => setConfirming(false)} /> : <UserAccountForm account={account} draft={draft} onDraft={setDraft} security={security} onSecurity={setSecurity} saving={saving} canSave={!account || Object.keys(changes).length > 0} onSubmit={submit} onClose={onClose} />}
    </div>
  </Modal>;
}
