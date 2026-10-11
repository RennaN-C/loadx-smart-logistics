import { useState, type FormEvent } from "react";
import { FormField } from "../../../components/FormField";
import { useAuth } from "../hooks/useAuth";
import { updateOwnProfile } from "../api/accountApi";
import { accountError } from "./accountError";

export function OwnProfileForm() {
  const { user, updateUser } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (saving) return;
    setSaving(true); setError(null); setSuccess(false);
    try { updateUser(await updateOwnProfile(name.trim(), email.trim())); setSuccess(true); }
    catch (error_) { setError(accountError(error_)); }
    finally { setSaving(false); }
  }
  function cancel() { setName(user?.name ?? ""); setEmail(user?.email ?? ""); setError(null); setSuccess(false); }
  return <form className="entity-form account-form" onSubmit={save} aria-label="Dados pessoais" aria-busy={saving}>
    <div className="account-fields">
      <FormField id="account-name" label="Nome"><input id="account-name" autoComplete="name" value={name} required maxLength={120} disabled={saving} onChange={(e) => setName(e.target.value)} /></FormField>
      <FormField id="account-email" label="E-mail"><input id="account-email" type="email" autoComplete="email" value={email} required maxLength={255} disabled={saving} onChange={(e) => setEmail(e.target.value)} /></FormField>
    </div>
    <p>Perfil de acesso: <strong>{user ? { ADMIN: "Administrador", LOGISTICS_MANAGER: "Gestor de logística", CHECKER: "Conferente", DRIVER: "Motorista" }[user.role] : ""}</strong> (somente leitura).</p>
    {error && <p role="alert">{error}</p>}{success && <output>Dados pessoais salvos com sucesso.</output>}
    <div className="account-actions"><button className="btn-primary" disabled={saving} type="submit">{saving ? "Salvando…" : "Salvar dados pessoais"}</button><button className="btn-secondary" disabled={saving} type="button" onClick={cancel}>Cancelar</button></div>
  </form>;
}
