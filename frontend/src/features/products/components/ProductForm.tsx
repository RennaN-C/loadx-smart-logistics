import { useState, type FormEvent } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { createProduct, updateProduct } from "../api/productsApi";
import type { Product } from "../types";
import { mapProductErrorToMessage } from "./productsErrorMessages";

const volumeFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

function toNumber(value: string): number {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

interface ProductFormProps {
  /** Ausente = criação. Presente = edição do produto informado. */
  readonly product?: Product;
  readonly onSaved: () => void;
  readonly onCancel: () => void;
}

export function ProductForm({ product, onSaved, onCancel }: ProductFormProps) {
  const isEditing = product !== undefined;
  const [code, setCode] = useState(product?.code ?? "");
  const [name, setName] = useState(product?.name ?? "");
  const [description, setDescription] = useState(product?.description ?? "");
  const [width, setWidth] = useState(product ? String(product.widthCm) : "");
  const [height, setHeight] = useState(product ? String(product.heightCm) : "");
  const [length, setLength] = useState(product ? String(product.lengthCm) : "");
  const [weight, setWeight] = useState(product ? String(product.weightKg) : "");
  const [fragile, setFragile] = useState(product?.fragile ?? false);
  const [stackable, setStackable] = useState(product?.stackable ?? true);
  const [rotationAllowed, setRotationAllowed] = useState(product?.rotationAllowed ?? true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const widthCm = toNumber(width);
  const heightCm = toNumber(height);
  const lengthCm = toNumber(length);
  const volumeM3 = (widthCm / 100) * (heightCm / 100) * (lengthCm / 100);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    const payload = {
      code: code.trim().toUpperCase(),
      name: name.trim(),
      description: description.trim() === "" ? null : description.trim(),
      widthCm,
      heightCm,
      lengthCm,
      weightKg: toNumber(weight),
      fragile,
      stackable,
      rotationAllowed,
    };

    try {
      if (product) {
        await updateProduct(product.id, payload);
      } else {
        await createProduct(payload);
      }
      onSaved();
    } catch (error) {
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapProductErrorToMessage(apiError));
      setIsSubmitting(false);
    }
  }

  return (
    <form className="entity-form" onSubmit={handleSubmit}>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <fieldset disabled={isSubmitting} className="entity-form-fieldset">
        <div className="entity-form-row">
          <div className="entity-form-field entity-form-field-narrow">
            <label className="field-label" htmlFor="product-code">
              CÓDIGO
            </label>
            <input
              id="product-code"
              name="code"
              required
              maxLength={64}
              placeholder="CX-100"
              value={code}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
            />
          </div>
          <div className="entity-form-field">
            <label className="field-label" htmlFor="product-name">
              NOME
            </label>
            <input
              id="product-name"
              name="name"
              required
              maxLength={160}
              placeholder="Caixa média"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
        </div>

        <div className="entity-form-field">
          <label className="field-label" htmlFor="product-description">
            DESCRIÇÃO (OPCIONAL)
          </label>
          <textarea
            id="product-description"
            name="description"
            rows={2}
            placeholder="Papelão reforçado, dupla parede"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>

        <p className="field-label">DIMENSÕES DO VOLUME</p>
        <div className="entity-form-box">
          <div className="entity-form-row">
            <div className="entity-form-field">
              <label className="field-label" htmlFor="product-width">
                LARGURA (CM)
              </label>
              <input
                id="product-width"
                name="widthCm"
                type="number"
                min={1}
                required
                placeholder="40"
                value={width}
                onChange={(event) => setWidth(event.target.value)}
              />
            </div>
            <div className="entity-form-field">
              <label className="field-label" htmlFor="product-height">
                ALTURA (CM)
              </label>
              <input
                id="product-height"
                name="heightCm"
                type="number"
                min={1}
                required
                placeholder="30"
                value={height}
                onChange={(event) => setHeight(event.target.value)}
              />
            </div>
            <div className="entity-form-field">
              <label className="field-label" htmlFor="product-length">
                COMPRIMENTO (CM)
              </label>
              <input
                id="product-length"
                name="lengthCm"
                type="number"
                min={1}
                required
                placeholder="60"
                value={length}
                onChange={(event) => setLength(event.target.value)}
              />
            </div>
            <div className="entity-form-field">
              <label className="field-label" htmlFor="product-weight">
                PESO (KG)
              </label>
              <input
                id="product-weight"
                name="weightKg"
                type="number"
                min={0.001}
                step="0.001"
                required
                placeholder="12,5"
                value={weight}
                onChange={(event) => setWeight(event.target.value)}
              />
            </div>
          </div>

          <dl className="entity-form-derived">
            <div>
              <dt>Volume unitário</dt>
              <dd>{volumeFormatter.format(volumeM3)} m³</dd>
            </div>
          </dl>
        </div>

        <p className="field-label">RESTRIÇÕES DE CARREGAMENTO</p>
        <p className="entity-form-help">
          É por estas opções que o otimizador decide onde o volume pode ficar e o que pode ser empilhado em
          cima dele.
        </p>
        <div className="entity-form-checks">
          <label htmlFor="product-fragile">
            <input
              id="product-fragile"
              name="fragile"
              type="checkbox"
              checked={fragile}
              onChange={(event) => setFragile(event.target.checked)}
            />
            <span>
              Frágil
              <small>Não recebe peso em cima</small>
            </span>
          </label>
          <label htmlFor="product-stackable">
            <input
              id="product-stackable"
              name="stackable"
              type="checkbox"
              checked={stackable}
              onChange={(event) => setStackable(event.target.checked)}
            />
            <span>
              Empilhável
              <small>Pode ser usado como base para outros volumes</small>
            </span>
          </label>
          <label htmlFor="product-rotation">
            <input
              id="product-rotation"
              name="rotationAllowed"
              type="checkbox"
              checked={rotationAllowed}
              onChange={(event) => setRotationAllowed(event.target.checked)}
            />
            <span>
              Rotação permitida
              <small>O otimizador pode girar o volume para encaixar</small>
            </span>
          </label>
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
            <span>{isEditing ? "Salvar alterações" : "Cadastrar produto"}</span>
          )}
        </button>
      </div>
    </form>
  );
}
