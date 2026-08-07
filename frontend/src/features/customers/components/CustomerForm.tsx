import { useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { ApiError } from "../../../types/api";
import { createCustomer, updateCustomer } from "../api/customersApi";
import type { Customer } from "../types";
import { mapCustomerErrorToMessage } from "./customersErrorMessages";

function orNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

interface CustomerFormProps {
  /** Ausente = criação. Presente = edição do cliente informado. */
  readonly customer?: Customer;
  readonly onSaved: () => void;
  readonly onCancel: () => void;
}

export function CustomerForm({ customer, onSaved, onCancel }: CustomerFormProps) {
  const isEditing = customer !== undefined;
  const [name, setName] = useState(customer?.name ?? "");
  const [document, setDocument] = useState(customer?.document ?? "");
  const [phone, setPhone] = useState(customer?.phone ?? "");
  const [address, setAddress] = useState(customer?.address ?? "");
  const [city, setCity] = useState(customer?.city ?? "");
  const [state, setState] = useState(customer?.state ?? "");
  const [notes, setNotes] = useState(customer?.notes ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    const payload = {
      name: name.trim(),
      document: document.trim(),
      phone: orNull(phone),
      address: address.trim(),
      city: city.trim(),
      state: state.trim().toUpperCase(),
      notes: orNull(notes),
    };

    try {
      if (customer) {
        await updateCustomer(customer.id, payload);
      } else {
        await createCustomer(payload);
      }
      onSaved();
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapCustomerErrorToMessage(apiError));
      setIsSubmitting(false);
    }
  }

  return (
    <form className="entity-form" onSubmit={handleSubmit}>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <fieldset disabled={isSubmitting} className="entity-form-fieldset">
        <div className="entity-form-row">
          <FormField id="customer-name" label="NOME OU RAZÃO SOCIAL">
            <input
              id="customer-name"
              name="name"
              required
              maxLength={160}
              placeholder="Distribuidora Aurora"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </FormField>
          <FormField id="customer-document" label="DOCUMENTO" narrow>
            <input
              id="customer-document"
              name="document"
              required
              maxLength={32}
              placeholder="CNPJ ou CPF"
              value={document}
              onChange={(event) => setDocument(event.target.value)}
            />
          </FormField>
        </div>

        <div className="entity-form-row">
          <FormField id="customer-address" label="ENDEREÇO">
            <input
              id="customer-address"
              name="address"
              required
              maxLength={255}
              placeholder="Rua das Palmeiras, 120"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
            />
          </FormField>
          <FormField id="customer-phone" label="TELEFONE (OPCIONAL)" narrow>
            <input
              id="customer-phone"
              name="phone"
              maxLength={32}
              placeholder="(11) 90000-0000"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
            />
          </FormField>
        </div>

        <div className="entity-form-row">
          <FormField id="customer-city" label="CIDADE">
            <input
              id="customer-city"
              name="city"
              required
              maxLength={120}
              placeholder="Campinas"
              value={city}
              onChange={(event) => setCity(event.target.value)}
            />
          </FormField>
          <FormField id="customer-state" label="UF" narrow>
            <input
              id="customer-state"
              name="state"
              required
              minLength={2}
              maxLength={2}
              placeholder="SP"
              value={state}
              onChange={(event) => setState(event.target.value.toUpperCase())}
            />
          </FormField>
        </div>

        <FormField id="customer-notes" label="OBSERVAÇÕES (OPCIONAL)">
          <textarea
            id="customer-notes"
            name="notes"
            rows={2}
            placeholder="Recebe carga só até as 16h"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </FormField>
      </fieldset>

      <div className="entity-form-actions">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancelar
        </button>
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="spinner" aria-hidden="true" />
              <span>Salvando…</span>
            </>
          ) : (
            <span>{isEditing ? "Salvar alterações" : "Cadastrar cliente"}</span>
          )}
        </button>
      </div>
    </form>
  );
}
