import { useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import {
  isCompleteDocument,
  isCompletePhone,
  maskDocument,
  maskPhone,
  onlyDigits,
} from "../../../components/masks";
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
  // Mascarado ao entrar: o banco guarda dígitos, a tela mostra formatado.
  const [document, setDocument] = useState(maskDocument(customer?.document ?? ""));
  const [phone, setPhone] = useState(maskPhone(customer?.phone ?? ""));
  const [address, setAddress] = useState(customer?.address ?? "");
  const [city, setCity] = useState(customer?.city ?? "");
  const [state, setState] = useState(customer?.state ?? "");
  const [notes, setNotes] = useState(customer?.notes ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    // Barra antes de sair da tela: o backend aceita texto livre em `document`,
    // então um CPF pela metade seria GRAVADO sem reclamação nenhuma.
    if (!isCompleteDocument(document)) {
      setErrorMessage(
        "Documento incompleto. Informe um CPF com 11 dígitos ou um CNPJ com 14.",
      );
      return;
    }
    if (phone.trim() !== "" && !isCompletePhone(phone)) {
      setErrorMessage("Telefone incompleto. Informe DDD e número, com 10 ou 11 dígitos.");
      return;
    }

    setIsSubmitting(true);

    const payload = {
      name: name.trim(),
      // Só os dígitos viajam: a unicidade do documento é comparada como string
      // no backend, e gravar ora com pontuação ora sem deixaria o mesmo CPF
      // entrar duas vezes.
      document: onlyDigits(document),
      phone: phone.trim() === "" ? null : onlyDigits(phone),
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
          <FormField
            id="customer-document"
            label="DOCUMENTO"
            tooltip="CPF ou CNPJ do cliente. Digite só os números: a formatação é aplicada sozinha, e o sistema guarda apenas os dígitos."
            narrow
          >
            <input
              id="customer-document"
              name="document"
              required
              inputMode="numeric"
              maxLength={18}
              placeholder="CPF ou CNPJ"
              value={document}
              onChange={(event) => setDocument(maskDocument(event.target.value))}
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
          <FormField
            id="customer-phone"
            label="TELEFONE (OPCIONAL)"
            tooltip="Com DDD. Aceita fixo, com 10 dígitos, e celular, com 11."
            narrow
          >
            <input
              id="customer-phone"
              name="phone"
              inputMode="tel"
              maxLength={15}
              placeholder="(11) 90000-0000"
              value={phone}
              onChange={(event) => setPhone(maskPhone(event.target.value))}
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
