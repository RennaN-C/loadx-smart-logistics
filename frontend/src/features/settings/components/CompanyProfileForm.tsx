import { useEffect, useRef, useState, type FormEvent } from "react";
import { FormField } from "../../../components/FormField";
import { fieldErrorProps } from "../../../components/fieldErrorProps";
import { validationFieldMessages, validationMessage } from "../../../services/validationErrors";
import { ApiError } from "../../../types/api";
import { AuditTrail } from "../../audit/components/AuditTrail";
import { getCompanyProfile, updateCompanyProfile, type CompanyProfile, type CompanyProfileInput } from "../api/companyProfileApi";
import "./CompanyProfileForm.css";

const EMPTY: CompanyProfileInput = { legal_name: "", display_name: "", cnpj: null, phone: null, email: null, logo_reference: null };
const FIELDS = [
  { key: "legal_name", label: "Nome empresarial", max: 160, required: true, type: "text" },
  { key: "display_name", label: "Nome de exibição", max: 160, required: true, type: "text" },
  { key: "cnpj", label: "CNPJ", max: 18, required: false, type: "text" },
  { key: "phone", label: "Telefone", max: 20, required: false, type: "tel" },
  { key: "email", label: "E-mail institucional", max: 255, required: false, type: "email" },
  { key: "logo_reference", label: "Referência de logotipo", max: 2048, required: false, type: "url" },
] as const;
const LABELS = Object.fromEntries(FIELDS.map((field) => [field.key, field.label]));

export function CompanyProfileForm() {
  const [stored, setStored] = useState<CompanyProfile | null>(null);
  const [draft, setDraft] = useState<CompanyProfileInput>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Readonly<Record<string, string>>>({});
  const [success, setSuccess] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getCompanyProfile().then((value) => {
      if (!active) return;
      setStored(value); setDraft(value ?? EMPTY); setLoaded(true);
    }).catch(() => { if (active) setError("Não foi possível consultar os dados da empresa."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [retry]);
  function cancel() {
    setDraft(stored ?? EMPTY); setEditing(false); setErrors({}); setError(null); setSuccess(false);
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (saving || !editing) return;
    setSaving(true); setError(null); setErrors({}); setSuccess(false);
    const input = Object.fromEntries(FIELDS.map(({ key }) => [key, draft[key]?.trim() || (key === "legal_name" || key === "display_name" ? "" : null)])) as unknown as CompanyProfileInput;
    try {
      const value = await updateCompanyProfile(input);
      setStored(value); setDraft(value); setEditing(false); setSuccess(true);
    } catch (error_) {
      if (error_ instanceof ApiError) {
        setErrors(validationFieldMessages(error_));
        setError(validationMessage(error_, LABELS) ?? error_.message);
      } else setError("Não foi possível salvar os dados da empresa. Tente novamente.");
    } finally { setSaving(false); }
  }
  useEffect(() => {
    if (Object.keys(errors).length) form.current?.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus();
  }, [errors]);
  if (loading) return <output className="company-profile-feedback">Carregando dados da empresa…</output>;
  if (!loaded) return <div><p role="alert">{error}</p><button type="button" className="btn-secondary" onClick={() => setRetry((value) => value + 1)}>Tentar novamente</button></div>;
  return <>
    <p>Cadastro institucional do LoadX. Campos opcionais podem ficar em branco.</p>
    {!stored && <p>A empresa ainda não possui dados institucionais cadastrados.</p>}
    {error && <p role="alert" className="entity-form-error">{error}</p>}
    {success && <output className="company-profile-feedback">Dados da empresa salvos com sucesso.</output>}
    <form className="entity-form company-profile-form" ref={form} onSubmit={save} aria-label="Dados institucionais da empresa" aria-busy={saving}>
      <div className="company-profile-fields">
        {FIELDS.map((field) => {
          const id = `company-${field.key}`;
          return <FormField key={field.key} id={id} label={field.label} error={errors[field.key]} hint={field.key === "logo_reference" ? "URL HTTPS sem credenciais. Apenas referência; não envia nem carrega arquivos." : undefined}>
            <input id={id} name={field.key} type={field.type} maxLength={field.max} required={editing && field.required} readOnly={!editing} disabled={saving} value={draft[field.key] ?? ""} {...fieldErrorProps(id, errors[field.key])} onChange={(event) => setDraft((value) => ({ ...value, [field.key]: event.target.value }))} />
          </FormField>;
        })}
      </div>
      <div className="company-profile-actions">
        {editing ? <><button type="submit" className="btn-primary" disabled={saving}>{saving ? "Salvando…" : "Salvar dados da empresa"}</button><button type="button" className="btn-secondary" disabled={saving} onClick={cancel}>Cancelar</button></> : <button type="button" className="btn-primary" onClick={() => { setEditing(true); setSuccess(false); }}>{stored ? "Editar dados da empresa" : "Cadastrar dados da empresa"}</button>}
      </div>
    </form>
    {stored && <AuditTrail key={stored.updated_at} entityType="COMPANY_PROFILE" entityId={stored.id} title="Histórico de alterações da empresa" />}
  </>;
}
