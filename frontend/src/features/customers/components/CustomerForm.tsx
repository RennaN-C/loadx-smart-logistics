import { useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { EntityNameField } from "../../../components/EntityNameField";
import { FormField } from "../../../components/FormField";
import { fieldErrorProps } from "../../../components/fieldErrorProps";
import { validateCustomerDocument, validatePhone } from "../../../components/documentRules";
import { maskDocument, maskPhone, onlyDigits } from "../../../components/masks";
import { useFieldErrors } from "../../../hooks/useFieldErrors";
import { createCustomer, updateCustomer } from "../api/customersApi";
import type { CepAddress, Customer } from "../types";
import { CepLookupField } from "./CepLookupField";
import { mapCustomerErrorToMessage } from "./customersErrorMessages";

function orNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

const NAME = "customer-name";
const DOCUMENT = "customer-document";
const PHONE = "customer-phone";
const ADDRESS = "customer-address";
const CITY = "customer-city";
const STATE = "customer-state";
const NOTES = "customer-notes";

const CUSTOMER_NAME_FIELD = {
  id: NAME,
  label: "NOME OU RAZÃO SOCIAL",
  placeholder: "Distribuidora Aurora",
} as const;

/** Campo do payload → controle da tela, para o 422 pousar no lugar certo. */
const API_FIELD_TO_CONTROL: Readonly<Record<string, string>> = {
  name: NAME,
  document: DOCUMENT,
  phone: PHONE,
  address: ADDRESS,
  city: CITY,
  state: STATE,
  notes: NOTES,
};

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
  const { errors, formRef, validateAll, revalidate, submissionErrorMessage } =
    useFieldErrors(API_FIELD_TO_CONTROL);

  function handleDocumentChange(value: string) {
    const masked = maskDocument(value);
    setDocument(masked);
    revalidate(DOCUMENT, () => validateCustomerDocument(masked));
  }

  /**
   * Preenchimento vindo do CEP (OC70). Os campos continuam editáveis: número e
   * complemento são justamente o que a consulta não tem como saber.
   */
  function handleCepFound(found: CepAddress) {
    setCity(found.city);
    setState(found.state);

    // Não sobrescreve quando a rua já está lá: quem digitou "Rua X, 120" e só
    // depois preencheu o CEP perderia o número.
    if (found.street !== null && !address.trim().startsWith(found.street)) {
      setAddress(found.street);
    }
  }

  function handlePhoneChange(value: string) {
    const masked = maskPhone(value);
    setPhone(masked);
    revalidate(PHONE, () => validatePhone(masked, { required: false }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    // Barra antes de sair da tela, com a MESMA regra da OC63. O backend recusaria
    // de qualquer jeito; a diferença é a pessoa descobrir agora, no campo, em vez
    // de depois do envio numa faixa que não diz qual campo errou.
    const podeEnviar = validateAll({
      [DOCUMENT]: () => validateCustomerDocument(document),
      [PHONE]: () => validatePhone(phone, { required: false }),
    });
    if (!podeEnviar) return;

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
      setErrorMessage(submissionErrorMessage(error, mapCustomerErrorToMessage));
      setIsSubmitting(false);
    }
  }

  return (
    <form className="entity-form" ref={formRef} onSubmit={handleSubmit}>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <fieldset disabled={isSubmitting} className="entity-form-fieldset">
        <div className="entity-form-row">
          <EntityNameField
            config={CUSTOMER_NAME_FIELD}
            value={name}
            onChange={setName}
            error={errors[NAME]}
          />
          <FormField
            id={DOCUMENT}
            label="DOCUMENTO"
            tooltip="CPF ou CNPJ do cliente. Digite só os números: a formatação é aplicada sozinha, e o sistema guarda apenas os dígitos."
            error={errors[DOCUMENT]}
            narrow
          >
            <input
              id={DOCUMENT}
              name="document"
              required
              inputMode="numeric"
              maxLength={18}
              placeholder="CPF ou CNPJ"
              value={document}
              onChange={(event) => handleDocumentChange(event.target.value)}
              {...fieldErrorProps(DOCUMENT, errors[DOCUMENT])}
            />
          </FormField>
        </div>

        <div className="entity-form-row">
          <CepLookupField onFound={handleCepFound} />
          <FormField id={ADDRESS} label="ENDEREÇO" error={errors[ADDRESS]}>
            <input
              id={ADDRESS}
              name="address"
              required
              maxLength={255}
              placeholder="Rua das Palmeiras, 120"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              {...fieldErrorProps(ADDRESS, errors[ADDRESS])}
            />
          </FormField>
        </div>

        <div className="entity-form-row">
          <FormField id={CITY} label="CIDADE" error={errors[CITY]}>
            <input
              id={CITY}
              name="city"
              required
              maxLength={120}
              placeholder="Campinas"
              value={city}
              onChange={(event) => setCity(event.target.value)}
              {...fieldErrorProps(CITY, errors[CITY])}
            />
          </FormField>
          <FormField id={STATE} label="UF" error={errors[STATE]} narrow>
            <input
              id={STATE}
              name="state"
              required
              minLength={2}
              maxLength={2}
              placeholder="SP"
              value={state}
              onChange={(event) => setState(event.target.value.toUpperCase())}
              {...fieldErrorProps(STATE, errors[STATE])}
            />
          </FormField>
          <FormField
            id={PHONE}
            label="TELEFONE (OPCIONAL)"
            tooltip="Com DDD. Aceita fixo, com 10 dígitos, e celular, com 11."
            error={errors[PHONE]}
            narrow
          >
            <input
              id={PHONE}
              name="phone"
              inputMode="tel"
              maxLength={15}
              placeholder="(11) 90000-0000"
              value={phone}
              onChange={(event) => handlePhoneChange(event.target.value)}
              {...fieldErrorProps(PHONE, errors[PHONE])}
            />
          </FormField>
        </div>

        <FormField id={NOTES} label="OBSERVAÇÕES (OPCIONAL)" error={errors[NOTES]}>
          <textarea
            id={NOTES}
            name="notes"
            rows={2}
            placeholder="Recebe carga só até as 16h"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            {...fieldErrorProps(NOTES, errors[NOTES])}
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
