import { useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { EntityNameField } from "../../../components/EntityNameField";
import { FormField } from "../../../components/FormField";
import { fieldErrorProps } from "../../../components/fieldErrorProps";
import { validateCnh, validateDriverDocument, validatePhone } from "../../../components/documentRules";
import { maskDocument, maskPhone, onlyDigits } from "../../../components/masks";
import { useFieldErrors } from "../../../hooks/useFieldErrors";
import { createDriver, updateDriver } from "../api/driversApi";
import type { Driver } from "../types";
import { mapDriverErrorToMessage } from "./driversErrorMessages";

/** Categorias que dirigem caminhão; A é moto e B é carro de passeio. */
const LICENSE_CATEGORIES = ["C", "D", "E", "AC", "AD", "AE"];

/** A CNH não tem máscara oficial: são 11 dígitos, e é só isso que o backend aceita. */
const CNH_LENGTH = 11;

const NAME = "driver-name";
const DOCUMENT = "driver-document";
const PHONE = "driver-phone";
const LICENSE = "driver-license";
const CATEGORY = "driver-category";

const DRIVER_NAME_FIELD = {
  id: NAME,
  label: "NOME",
  placeholder: "Carlos Pereira",
} as const;

/** Campo do payload → controle da tela, para o 422 pousar no lugar certo. */
const API_FIELD_TO_CONTROL: Readonly<Record<string, string>> = {
  name: NAME,
  document: DOCUMENT,
  phone: PHONE,
  license_number: LICENSE,
  license_category: CATEGORY,
};

interface DriverFormProps {
  /** Ausente = criação. Presente = edição do motorista informado. */
  readonly driver?: Driver;
  readonly onSaved: () => void;
  readonly onCancel: () => void;
}

export function DriverForm({ driver, onSaved, onCancel }: DriverFormProps) {
  const isEditing = driver !== undefined;
  const [name, setName] = useState(driver?.name ?? "");
  // Mascarado ao entrar: o banco guarda dígitos, a tela mostra formatado.
  const [document, setDocument] = useState(maskDocument(driver?.document ?? ""));
  const [phone, setPhone] = useState(maskPhone(driver?.phone ?? ""));
  const [licenseNumber, setLicenseNumber] = useState(onlyDigits(driver?.licenseNumber ?? ""));
  const [licenseCategory, setLicenseCategory] = useState(driver?.licenseCategory ?? "");
  const [active, setActive] = useState(driver?.active ?? true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { errors, formRef, validateAll, revalidate, submissionErrorMessage } =
    useFieldErrors(API_FIELD_TO_CONTROL);

  function handleDocumentChange(value: string) {
    const masked = maskDocument(value);
    setDocument(masked);
    revalidate(DOCUMENT, () => validateDriverDocument(masked));
  }

  function handlePhoneChange(value: string) {
    const masked = maskPhone(value);
    setPhone(masked);
    revalidate(PHONE, () => validatePhone(masked, { required: true }));
  }

  function handleLicenseChange(value: string) {
    // O campo só aceita dígito porque o backend só aceita dígito: o padrão da
    // OC63 para CNH é `[0-9]{11}`, sem máscara nenhuma. Antes daqui, quem
    // digitasse "012.345.678-90" levava 422 sem entender por quê.
    const digits = onlyDigits(value).slice(0, CNH_LENGTH);
    setLicenseNumber(digits);
    revalidate(LICENSE, () => validateCnh(digits));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    const podeEnviar = validateAll({
      // Motorista é sempre pessoa física, então aqui o documento é CPF.
      [DOCUMENT]: () => validateDriverDocument(document),
      [PHONE]: () => validatePhone(phone, { required: true }),
      [LICENSE]: () => validateCnh(licenseNumber),
    });
    if (!podeEnviar) return;

    setIsSubmitting(true);

    const payload = {
      name: name.trim(),
      // Só os dígitos: a unicidade do documento e da CNH é comparada como
      // string no backend, e misturar formatos deixaria duplicata passar.
      document: onlyDigits(document),
      phone: onlyDigits(phone),
      licenseNumber: onlyDigits(licenseNumber),
      licenseCategory: licenseCategory === "" ? null : licenseCategory,
    };

    try {
      if (driver) {
        await updateDriver(driver.id, { ...payload, active });
      } else {
        await createDriver(payload);
      }
      onSaved();
    } catch (error) {
      setErrorMessage(submissionErrorMessage(error, mapDriverErrorToMessage));
      setIsSubmitting(false);
    }
  }

  return (
    <form className="entity-form" ref={formRef} onSubmit={handleSubmit}>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <fieldset disabled={isSubmitting} className="entity-form-fieldset">
        <div className="entity-form-row">
          <EntityNameField
            config={DRIVER_NAME_FIELD}
            value={name}
            onChange={setName}
            error={errors[NAME]}
          />
          <FormField
            id={DOCUMENT}
            label="DOCUMENTO"
            tooltip="CPF do motorista. Digite só os números: a formatação é aplicada sozinha."
            error={errors[DOCUMENT]}
            narrow
          >
            <input
              id={DOCUMENT}
              name="document"
              required
              inputMode="numeric"
              maxLength={14}
              placeholder="CPF"
              value={document}
              onChange={(event) => handleDocumentChange(event.target.value)}
              {...fieldErrorProps(DOCUMENT, errors[DOCUMENT])}
            />
          </FormField>
        </div>

        <div className="entity-form-row">
          <FormField
            id={PHONE}
            label="TELEFONE"
            tooltip="Com DDD. Aceita fixo, com 10 dígitos, e celular, com 11."
            error={errors[PHONE]}
          >
            <input
              id={PHONE}
              name="phone"
              required
              inputMode="tel"
              maxLength={15}
              placeholder="(11) 90000-0000"
              value={phone}
              onChange={(event) => handlePhoneChange(event.target.value)}
              {...fieldErrorProps(PHONE, errors[PHONE])}
            />
          </FormField>
          <FormField
            id={LICENSE}
            label="NÚMERO DA CNH"
            tooltip="Número de registro impresso na carteira, com 11 dígitos. Não é o CPF."
            error={errors[LICENSE]}
          >
            <input
              id={LICENSE}
              name="licenseNumber"
              required
              inputMode="numeric"
              maxLength={CNH_LENGTH}
              placeholder="01234567890"
              value={licenseNumber}
              onChange={(event) => handleLicenseChange(event.target.value)}
              {...fieldErrorProps(LICENSE, errors[LICENSE])}
            />
          </FormField>
          <FormField
            id={CATEGORY}
            label="CATEGORIA (OPCIONAL)"
            tooltip="Categoria da CNH: C, D ou E habilitam carga. Deixe em branco se não souber."
            error={errors[CATEGORY]}
            narrow
          >
            <select
              id={CATEGORY}
              name="licenseCategory"
              value={licenseCategory}
              onChange={(event) => setLicenseCategory(event.target.value)}
              {...fieldErrorProps(CATEGORY, errors[CATEGORY])}
            >
              <option value="">Não informada</option>
              {LICENSE_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </FormField>
        </div>

        {isEditing ? (
          <div className="entity-form-checks">
            <label htmlFor="driver-active">
              <input
                id="driver-active"
                name="active"
                type="checkbox"
                checked={active}
                onChange={(event) => setActive(event.target.checked)}
              />
              <span>
                Motorista ativo
                <small>Motoristas arquivados continuam no histórico, mas saem da operação.</small>
              </span>
            </label>
          </div>
        ) : null}
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
            <span>{isEditing ? "Salvar alterações" : "Cadastrar motorista"}</span>
          )}
        </button>
      </div>
    </form>
  );
}
