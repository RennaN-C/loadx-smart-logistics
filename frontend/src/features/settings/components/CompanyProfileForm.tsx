import { useEffect, useRef, useState, type FormEvent } from "react";
import { Icon } from "../../../components/Icon";
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
const GROUPS = [
  { id: "identity", title: "Identificação da empresa", description: "Nome institucional e identificação fiscal da empresa.", icon: "orders", fields: ["legal_name", "display_name", "cnpj"] },
  { id: "contact", title: "Canais de contato", description: "Informações institucionais para contato com a empresa.", icon: "users", fields: ["phone", "email"] },
  { id: "brand", title: "Referência de marca", description: "Endereço de referência do logotipo, sem envio de arquivos.", icon: "settings", fields: ["logo_reference"] },
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
  useEffect(() => {
    if (editing) form.current?.querySelector<HTMLInputElement>("input")?.focus();
  }, [editing]);
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
    {error && <p role="alert" className="entity-form-error">{error}</p>}
    {success && <output className="company-profile-feedback company-profile-success">Dados da empresa salvos com sucesso.</output>}
    <form className="entity-form company-profile-form" ref={form} onSubmit={save} aria-label="Dados institucionais da empresa" aria-busy={saving}>
      <div className="company-profile-toolbar"><p>{stored ? "Cadastro institucional do LoadX." : "A empresa ainda não possui dados institucionais cadastrados."}<span>Campos opcionais podem ficar em branco.</span></p><span className="settings-readonly">{editing ? "Em edição" : "Somente leitura"}</span></div>
      {GROUPS.map((group) => <section className="company-profile-card" key={group.id} aria-labelledby={`company-group-${group.id}`}>
        <div className="company-profile-card-heading"><span className="settings-card-icon"><Icon name={group.icon} size={20} /></span><div><h3 id={`company-group-${group.id}`}>{group.title}</h3><p>{group.description}</p></div></div>
        <div className="company-profile-fields">
          {FIELDS.filter((field) => (group.fields as readonly string[]).includes(field.key)).map((field) => {
            const id = `company-${field.key}`;
            return <div key={field.key} className={field.key === "legal_name" || field.key === "logo_reference" ? "company-profile-field company-profile-field-wide" : "company-profile-field"}>
              <FormField id={id} label={field.label} error={errors[field.key]} hint={field.key === "logo_reference" ? "URL HTTPS sem credenciais. Apenas referência; não envia nem carrega arquivos." : undefined}>
                <span id={`${id}-requirement`} className="company-field-requirement">{field.required ? "Obrigatório" : "Opcional"}</span>
                <input id={id} name={field.key} type={field.type} maxLength={field.max} required={editing && field.required} readOnly={!editing} disabled={saving} value={draft[field.key] ?? ""} {...fieldErrorProps(id, errors[field.key])} aria-describedby={errors[field.key] ? `${id}-error` : `${id}-requirement`} onChange={(event) => setDraft((value) => ({ ...value, [field.key]: event.target.value }))} />
              </FormField>
            </div>;
          })}
        </div>
      </section>)}
      <div className="company-profile-footer"><p>{editing ? "As alterações serão aplicadas após salvar." : "Para alterar as informações, ative a edição."}</p><div className="company-profile-actions">
        {editing ? <><button type="button" className="btn-secondary" disabled={saving} onClick={cancel}>Cancelar</button><button type="submit" className="btn-primary" disabled={saving}>{saving ? "Salvando…" : "Salvar dados da empresa"}</button></> : <button type="button" className="btn-primary" onClick={() => { setEditing(true); setSuccess(false); }}>{stored ? "Editar dados da empresa" : "Cadastrar dados da empresa"}</button>}
      </div></div>
    </form>
    {stored && <details className="company-profile-history"><summary>Histórico de alterações da empresa</summary><AuditTrail key={stored.updated_at} entityType="COMPANY_PROFILE" entityId={stored.id} title="Histórico de alterações da empresa" /></details>}
  </>;
}
