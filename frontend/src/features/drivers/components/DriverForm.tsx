import { useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
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
  const [document, setDocument] = useState(driver?.document ?? "");
  const [phone, setPhone] = useState(driver?.phone ?? "");
  const [licenseNumber, setLicenseNumber] = useState(driver?.licenseNumber ?? "");
  const [licenseCategory, setLicenseCategory] = useState(driver?.licenseCategory ?? "");
  const [active, setActive] = useState(driver?.active ?? true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    const payload = {
      name: name.trim(),
      document: document.trim(),
      phone: phone.trim(),
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
          <FormField id="driver-document" label="DOCUMENTO" narrow>
            <input
              id="driver-document"
              name="document"
              required
              maxLength={32}
              placeholder="CPF"
              value={document}
              onChange={(event) => setDocument(event.target.value)}
            />
          </FormField>
        </div>

        <div className="entity-form-row">
          <FormField id="driver-phone" label="TELEFONE">
            <input
              id="driver-phone"
              name="phone"
              required
              maxLength={32}
              placeholder="(11) 90000-0000"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
            />
          </FormField>
          <FormField id="driver-license" label="NÚMERO DA CNH">
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
          <FormField id="driver-category" label="CATEGORIA (OPCIONAL)" narrow>
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
