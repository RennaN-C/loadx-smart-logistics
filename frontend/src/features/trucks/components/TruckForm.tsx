import { useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { createTruck, updateTruck } from "../api/trucksApi";
import type { Truck } from "../types";
import { TruckSchematic } from "./TruckSchematic";
import { mapTruckErrorToMessage } from "./trucksErrorMessages";

const decimalFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function toNumber(value: string): number {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

interface TruckFormProps {
  /** Ausente = criação. Presente = edição do caminhão informado. */
  readonly truck?: Truck;
  readonly onSaved: () => void;
  readonly onCancel: () => void;
}

export function TruckForm({ truck, onSaved, onCancel }: TruckFormProps) {
  const isEditing = truck !== undefined;
  const [plate, setPlate] = useState(truck?.plate ?? "");
  const [model, setModel] = useState(truck?.model ?? "");
  const [width, setWidth] = useState(truck ? String(truck.internalWidthCm) : "");
  const [height, setHeight] = useState(truck ? String(truck.internalHeightCm) : "");
  const [length, setLength] = useState(truck ? String(truck.internalLengthCm) : "");
  const [weight, setWeight] = useState(truck ? String(truck.maxWeightKg) : "");
  const [active, setActive] = useState(truck?.active ?? true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const widthCm = toNumber(width);
  const heightCm = toNumber(height);
  const lengthCm = toNumber(length);
  const volumeM3 = (widthCm / 100) * (heightCm / 100) * (lengthCm / 100);
  const floorAreaM2 = (widthCm / 100) * (lengthCm / 100);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    const payload = {
      plate: plate.trim().toUpperCase(),
      model: model.trim(),
      internalWidthCm: widthCm,
      internalHeightCm: heightCm,
      internalLengthCm: lengthCm,
      maxWeightKg: toNumber(weight),
    };

    try {
      if (truck) {
        await updateTruck(truck.id, { ...payload, active });
      } else {
        await createTruck(payload);
      }
      onSaved();
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapTruckErrorToMessage(apiError));
      setIsSubmitting(false);
    }
  }

  return (
    <form className="entity-form" onSubmit={handleSubmit}>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <fieldset disabled={isSubmitting} className="entity-form-fieldset">
        <div className="entity-form-row">
          <div className="entity-form-field">
            <label className="field-label" htmlFor="truck-plate">
              PLACA
            </label>
            <input
              id="truck-plate"
              name="plate"
              required
              maxLength={16}
              placeholder="ABC1D23"
              value={plate}
              onChange={(event) => setPlate(event.target.value.toUpperCase())}
            />
          </div>
          <div className="entity-form-field">
            <label className="field-label" htmlFor="truck-model">
              MODELO
            </label>
            <input
              id="truck-model"
              name="model"
              required
              maxLength={120}
              placeholder="Baú médio"
              value={model}
              onChange={(event) => setModel(event.target.value)}
            />
          </div>
        </div>

        <p className="field-label">MEDIDAS INTERNAS DO BAÚ</p>
        <div className="truck-form-figure">
          <TruckSchematic dimensions={{ widthCm, heightCm, lengthCm }} view="side" variant="detailed" />
          <TruckSchematic dimensions={{ widthCm, heightCm, lengthCm }} view="rear" variant="detailed" />
        </div>
        <p className="entity-form-help">
          Meça pelo lado interno do baú: da parede frontal à face interna da porta traseira, entre as laterais, e
          do piso ao teto. É essa medida que o otimizador usa para calcular o encaixe da carga.
        </p>

        <div className="entity-form-box">
          <div className="entity-form-row">
            <div className="entity-form-field">
              <label className="field-label" htmlFor="truck-width">
                LARGURA (CM)
              </label>
              <input
                id="truck-width"
                name="internalWidthCm"
                type="number"
                min={1}
                required
                placeholder="240"
                value={width}
                onChange={(event) => setWidth(event.target.value)}
              />
            </div>
            <div className="entity-form-field">
              <label className="field-label" htmlFor="truck-height">
                ALTURA (CM)
              </label>
              <input
                id="truck-height"
                name="internalHeightCm"
                type="number"
                min={1}
                required
                placeholder="260"
                value={height}
                onChange={(event) => setHeight(event.target.value)}
              />
            </div>
            <div className="entity-form-field">
              <label className="field-label" htmlFor="truck-length">
                COMPRIMENTO (CM)
              </label>
              <input
                id="truck-length"
                name="internalLengthCm"
                type="number"
                min={1}
                required
                placeholder="600"
                value={length}
                onChange={(event) => setLength(event.target.value)}
              />
            </div>
          </div>

          <dl className="entity-form-derived">
            <div>
              <dt>Volume interno</dt>
              <dd>{decimalFormatter.format(volumeM3)} m³</dd>
            </div>
            <div>
              <dt>Área do piso</dt>
              <dd>{decimalFormatter.format(floorAreaM2)} m²</dd>
            </div>
          </dl>
        </div>

        <div className="entity-form-row">
          <div className="entity-form-field">
            <label className="field-label" htmlFor="truck-weight">
              PESO MÁXIMO (KG)
            </label>
            <input
              id="truck-weight"
              name="maxWeightKg"
              type="number"
              min={1}
              step="0.01"
              required
              placeholder="8000"
              value={weight}
              onChange={(event) => setWeight(event.target.value)}
            />
          </div>
          {isEditing ? (
            <div className="entity-form-checks">
              <label htmlFor="truck-active">
                <input
                  id="truck-active"
                  name="active"
                  type="checkbox"
                  checked={active}
                  onChange={(event) => setActive(event.target.checked)}
                />
                <span>Caminhão ativo</span>
              </label>
              <p className="entity-form-help">Caminhões inativos continuam no histórico, mas saem do planejamento.</p>
            </div>
          ) : null}
        </div>
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
            <span>{isEditing ? "Salvar alterações" : "Cadastrar caminhão"}</span>
          )}
        </button>
      </div>
    </form>
  );
}
