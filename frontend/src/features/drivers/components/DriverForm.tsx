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
import { createDriver, updateDriver } from "../api/driversApi";
import type { Driver } from "../types";
import { mapDriverErrorToMessage } from "./driversErrorMessages";

/** Categorias que dirigem caminhão; A é moto e B é carro de passeio. */
const LICENSE_CATEGORIES = ["C", "D", "E", "AC", "AD", "AE"];

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
  const [licenseNumber, setLicenseNumber] = useState(driver?.licenseNumber ?? "");
  const [licenseCategory, setLicenseCategory] = useState(driver?.licenseCategory ?? "");
  const [active, setActive] = useState(driver?.active ?? true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    // Motorista é sempre pessoa física, então aqui o documento é CPF.
    if (!isCompleteDocument(document)) {
      setErrorMessage("Documento incompleto. Informe um CPF com 11 dígitos.");
      return;
    }
    if (!isCompletePhone(phone)) {
      setErrorMessage("Telefone incompleto. Informe DDD e número, com 10 ou 11 dígitos.");
      return;
    }

    setIsSubmitting(true);

    const payload = {
      name: name.trim(),
      // Só os dígitos: a unicidade do documento e da CNH é comparada como
      // string no backend, e misturar formatos deixaria duplicata passar.
      document: onlyDigits(document),
      phone: onlyDigits(phone),
      licenseNumber: licenseNumber.trim(),
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
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapDriverErrorToMessage(apiError));
      setIsSubmitting(false);
    }
  }

  return (
    <form className="entity-form" onSubmit={handleSubmit}>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <fieldset disabled={isSubmitting} className="entity-form-fieldset">
        <div className="entity-form-row">
          <FormField id="driver-name" label="NOME">
            <input
              id="driver-name"
              name="name"
              required
              maxLength={160}
              placeholder="Carlos Pereira"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </FormField>
          <FormField
            id="driver-document" label="DOCUMENTO"
            tooltip="CPF do motorista. Digite só os números: a formatação é aplicada sozinha." narrow>
            <input
              id="driver-document"
              name="document"
              required
              inputMode="numeric"
              maxLength={14}
              placeholder="CPF"
              value={document}
              onChange={(event) => setDocument(maskDocument(event.target.value))}
            />
          </FormField>
        </div>

        <div className="entity-form-row">
          <FormField
            id="driver-phone" label="TELEFONE"
            tooltip="Com DDD. Aceita fixo, com 10 dígitos, e celular, com 11.">
            <input
              id="driver-phone"
              name="phone"
              required
              inputMode="tel"
              maxLength={15}
              placeholder="(11) 90000-0000"
              value={phone}
              onChange={(event) => setPhone(maskPhone(event.target.value))}
            />
          </FormField>
          <FormField
            id="driver-license" label="NÚMERO DA CNH"
            tooltip="Número de registro impresso na carteira, com 11 dígitos. Não é o CPF.">
            <input
              id="driver-license"
              name="licenseNumber"
              required
              maxLength={32}
              placeholder="01234567890"
              value={licenseNumber}
              onChange={(event) => setLicenseNumber(event.target.value)}
            />
          </FormField>
          <FormField
            id="driver-category" label="CATEGORIA (OPCIONAL)"
            tooltip="Categoria da CNH: C, D ou E habilitam carga. Deixe em branco se não souber." narrow>
            <select
              id="driver-category"
              name="licenseCategory"
              value={licenseCategory}
              onChange={(event) => setLicenseCategory(event.target.value)}
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
                <small>Motoristas inativos continuam no histórico, mas saem da operação.</small>
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
