import { useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { ApiError } from "../../../types/api";
import { createCustomerAddress, updateCustomerAddress } from "../api/customerAddressesApi";
import type { CustomerAddress } from "../types";
import { CepLookupField } from "./CepLookupField";

export function CustomerAddressForm({ customerId, address: original, onSaved, onCancel }: {
  readonly customerId: string;
  readonly address?: CustomerAddress;
  readonly onSaved: () => Promise<void>;
  readonly onCancel: () => void;
}) {
  const [label, setLabel] = useState(original?.label ?? "Entrega");
  const [address, setAddress] = useState(original?.address ?? "");
  const [city, setCity] = useState(original?.city ?? "");
  const [state, setState] = useState(original?.state ?? "");
  const [postalCode, setPostalCode] = useState(original?.postalCode ?? "");
  const [isPrimary, setIsPrimary] = useState(original?.isPrimary ?? false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function save(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const input = { label: label.trim(), address: address.trim(), city: city.trim(), state: state.trim().toUpperCase(), postalCode: postalCode || null, isPrimary, active: original?.active ?? true };
    try {
      if (original) await updateCustomerAddress(customerId, original.id, input);
      else await createCustomerAddress(customerId, input);
      await onSaved();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "Não foi possível salvar o endereço.");
    } finally { setPending(false); }
  }
  return <form className="entity-form" onSubmit={(event) => void save(event)}>
    {error ? <AlertBanner>{error}</AlertBanner> : null}
    <fieldset className="entity-form-fieldset" disabled={pending}>
      <FormField id="address-label" label="RÓTULO"><input id="address-label" required maxLength={80} value={label} onChange={(event) => setLabel(event.target.value)} /></FormField>
      <CepLookupField initialCep={postalCode} onCepChange={setPostalCode} onFound={(found) => {
        setCity(found.city); setState(found.state);
        if (found.street && !address.trim().startsWith(found.street)) setAddress(found.street);
      }} />
      <FormField id="address-text" label="ENDEREÇO"><input id="address-text" required maxLength={255} value={address} onChange={(event) => setAddress(event.target.value)} /></FormField>
      <FormField id="address-city" label="CIDADE"><input id="address-city" required maxLength={120} value={city} onChange={(event) => setCity(event.target.value)} /></FormField>
      <FormField id="address-state" label="UF"><input id="address-state" required minLength={2} maxLength={2} value={state} onChange={(event) => setState(event.target.value.toUpperCase())} /></FormField>
      <label><input type="checkbox" checked={isPrimary} onChange={(event) => setIsPrimary(event.target.checked)} /> Endereço principal</label>
    </fieldset>
    <div className="entity-form-actions">
      <button className="btn-secondary" type="button" disabled={pending} onClick={onCancel}>Cancelar endereço</button>
      <button className="btn-primary" type="submit" disabled={pending}>{pending ? "Salvando…" : "Salvar endereço"}</button>
    </div>
  </form>;
}
