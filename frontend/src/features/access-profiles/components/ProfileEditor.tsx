import { ProfileForm } from "./ProfileForm";
import { useEffect, useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { permissionCatalog, saveProfile, type AccessProfile, type PermissionDefinition, type ProfileInput } from "../api/profilesApi";
import { profileError } from "./profilePresentation";

export function ProfileEditor({ profile, onClose, onSaved, active = true }: { readonly active?: boolean; readonly profile?: AccessProfile; readonly onClose: () => void; readonly onSaved: () => void }) {
  const [draft, setDraft] = useState<ProfileInput>({ name: profile?.name ?? "", description: profile?.description ?? "", active: profile?.active ?? true, permissions: profile?.permissions ?? [] });
  const [catalog, setCatalog] = useState<PermissionDefinition[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { let current = true; setFailed(false); permissionCatalog().then((items) => { if (current) setCatalog(items); }).catch(() => { if (current) setFailed(true); }); return () => { current = false; }; }, [attempt]);
  useEffect(() => { if (active) document.getElementById(confirm ? "profile-confirm" : "profile-name")?.focus(); }, [confirm, catalog, active]);
  function submit(event: FormEvent) { event.preventDefault(); if (!saving && draft.name.trim()) setConfirm(true); }
  async function save() {
    if (saving) return;
    setSaving(true); setError(null);
    try { await saveProfile({ ...draft, name: draft.name.trim(), permissions: [...draft.permissions].sort((left, right) => left.localeCompare(right)) }, profile); onSaved(); }
    catch (error_) { setError(profileError(error_)); setConfirm(false); }
    finally { setSaving(false); }
  }
  if (!active) return null;
  return <Modal title={profile ? "Editar perfil" : "Criar perfil personalizado"} subtitle="Permissões locais do LoadX" onClose={() => { if (!saving) onClose(); }}>
    {error ? <AlertBanner>{error}</AlertBanner> : null}
    {failed ? <div><AlertBanner>Não foi possível consultar o catálogo de permissões.</AlertBanner><button className="btn-secondary" type="button" onClick={() => setAttempt((value) => value + 1)}>Tentar novamente</button></div> : null}
    {!catalog && !failed ? <output>Consultando permissões…</output> : null}
    {catalog && confirm ? <section aria-label="Confirmar perfil"><h3>Confirmar permissões</h3><p>O perfil <strong>{draft.name}</strong> terá {draft.permissions.length} permissões e ficará {draft.active ? "ativo" : "inativo"}.</p><p>Alterações de permissão encerram as sessões dos usuários associados. Permissões de leitura e gestão são independentes.</p><div className="user-actions"><button id="profile-confirm" className="btn-primary" type="button" disabled={saving} onClick={() => void save()}>{saving ? "Salvando…" : "Confirmar perfil"}</button><button className="btn-secondary" type="button" disabled={saving} onClick={() => setConfirm(false)}>Revisar permissões</button></div></section> : null}
    {catalog && !confirm ? <ProfileForm draft={draft} onDraft={setDraft} catalog={catalog} saving={saving} userCount={profile?.user_count ?? 0} onSubmit={submit} onClose={onClose} /> : null}
  </Modal>;
}
