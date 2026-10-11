import { useState, type FormEvent } from "react";
import { FormField } from "../../../components/FormField";
import { changeOwnPassword } from "../api/accountApi";
import { accountError } from "./accountError";
export function OwnPasswordForm({ onSignedOut }: { readonly onSignedOut: (notice: "password-changed") => void }) {
  const [current, setCurrent] = useState(""); const [password, setPassword] = useState(""); const [confirm, setConfirm] = useState("");
  const [visible, setVisible] = useState(false); const [saving, setSaving] = useState(false); const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (saving) { return; }
    setError(null);
    if (password !== confirm) { setError("A confirmação deve ser igual à nova senha."); return; }
    if (password.length < 15 || password.length > 128) { setError("A nova senha deve ter de 15 a 128 caracteres."); return; }
    setSaving(true);
    try { await changeOwnPassword(current, password); setCurrent(""); setPassword(""); setConfirm(""); onSignedOut("password-changed"); }
    catch (error_) { setError(accountError(error_)); }
    finally { setSaving(false); }
  }
  const fields = [{ id: "current", label: "Senha atual", value: current, setter: setCurrent, autoComplete: "current-password" }, { id: "new", label: "Nova senha", value: password, setter: setPassword, autoComplete: "new-password" }, { id: "confirm", label: "Confirmar nova senha", value: confirm, setter: setConfirm, autoComplete: "new-password" }];
  return <form className="entity-form account-form" aria-label="Alterar senha" onSubmit={submit} aria-busy={saving}>
    <p>Use de 15 a 128 caracteres; senhas comuns são recusadas. Após alterar a senha, todas as sessões serão encerradas e você precisará entrar novamente.</p>
    <div className="account-fields">{fields.map((field) => <FormField id={`password-${field.id}`} key={field.id} label={field.label}><input id={`password-${field.id}`} type={visible ? "text" : "password"} autoComplete={field.autoComplete} value={field.value} required maxLength={128} disabled={saving} onChange={(e) => field.setter(e.target.value)} /></FormField>)}</div>
    <button type="button" className="btn-secondary" aria-pressed={visible} onClick={() => setVisible((value) => !value)}>{visible ? "Ocultar senhas" : "Mostrar senhas"}</button>
    {error && <p role="alert">{error}</p>}
    <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Alterando…" : "Alterar senha"}</button>
  </form>;
}
