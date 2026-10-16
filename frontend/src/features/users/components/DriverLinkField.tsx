import { useCallback, useEffect, useState } from "react";
import { FormField } from "../../../components/FormField";
import { Pagination } from "../../../components/Pagination";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { getDriver, listDrivers } from "../../drivers/api/driversApi";

export function DriverLinkField({ value, onChange, disabled }: { readonly value: string | null; readonly onChange: (id: string | null) => void; readonly disabled: boolean }) {
  const [search, setSearch] = useState("");
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const load = useCallback((params: ListParams) => listDrivers({ ...params, search, archiveStatus: "all" }), [search]);
  const list = useResourceList(load);
  useEffect(() => {
    let current = true; setSelectedName(null);
    if (value) getDriver(value).then((driver) => { if (current) setSelectedName(`${driver.name}${driver.active ? "" : " (arquivado)"}`); }).catch(() => { if (current) setSelectedName("Vínculo atual — confira antes de salvar"); });
    return () => { current = false; };
  }, [value]);
  return <fieldset className="user-form-group"><legend>Vínculo operacional</legend>
    <p className="user-muted">O vínculo é opcional. Sem motorista ativo vinculado, esta conta não acessará viagens próprias.</p>
    <div className="user-form-grid">
      <FormField id="user-driver-search" label="Buscar motorista por nome"><input id="user-driver-search" type="search" maxLength={120} value={search} disabled={disabled} onChange={(event) => { setSearch(event.target.value); list.goToPage(1); }} /></FormField>
      <FormField id="user-driver" label="Motorista vinculado"><select id="user-driver" value={value ?? ""} disabled={disabled || list.status === "loading"} onChange={(event) => onChange(event.target.value || null)}>
        <option value="">Sem vínculo</option>
        {value && !list.items.some((driver) => driver.id === value) ? <option value={value}>{selectedName ?? "Consultando vínculo atual…"}</option> : null}
        {list.items.map((driver) => <option key={driver.id} value={driver.id}>{driver.name}{driver.active ? "" : " (arquivado)"}</option>)}
      </select></FormField>
    </div>
    {list.status === "loading" ? <output>Consultando motoristas…</output> : null}
    {list.status === "error" ? <p role="alert">Não foi possível consultar motoristas. <button type="button" className="btn-secondary" onClick={() => void list.refetch()}>Repetir consulta de motoristas</button></p> : null}
    <Pagination page={list.page} totalPages={list.totalPages} onChange={list.goToPage} label="motoristas para vínculo" />
  </fieldset>;
}
