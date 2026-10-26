import { useResourceList } from "../../../hooks/useResourceList";
import { FormField } from "../../../components/FormField";
import { Pagination } from "../../../components/Pagination";
import { listProfiles } from "../api/profilesApi";
export function ProfileAssignment({ value, onChange, disabled }: { readonly value: string | null; readonly onChange: (value: string | null) => void; readonly disabled: boolean }) {
  const list = useResourceList(listProfiles);
  return <fieldset className="user-form-group"><legend>Perfil personalizado</legend>
    <FormField id="user-custom-profile" label="Permissões de acesso"><select id="user-custom-profile" required value={value ?? ""} disabled={disabled || list.status === "loading"} onChange={(event) => onChange(event.target.value || null)}>
      <option value="">Selecione um perfil ativo</option>
      {value && !list.items.some((profile) => profile.id === value) ? <option value={value}>Perfil associado — preservado</option> : null}
      {list.items.filter((profile) => !profile.system_role && profile.active).map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
    </select></FormField>
    <p className="user-muted">Substitui o perfil anterior. A alteração encerra as sessões da conta.</p>
    {list.status === "error" ? <p role="alert">Não foi possível consultar os perfis. <button type="button" onClick={() => void list.refetch()}>Tentar novamente</button></p> : null}
    <Pagination page={list.page} totalPages={list.totalPages} onChange={list.goToPage} label="perfis disponíveis" />
  </fieldset>;
}
