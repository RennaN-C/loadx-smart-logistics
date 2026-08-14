import { useEffect, useMemo, useRef, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { getLoadPlanVisualization } from "../../load-planning/api/loadPlansApi";
import { REJECTION_LABELS, ROTATION_LABELS } from "../../load-planning/components/loadPlanLabels";
import { mapLoadPlanErrorToMessage } from "../../load-planning/components/loadPlansErrorMessages";
import type { LoadPlanVisualization, PlacedItem } from "../../load-planning/types";
import { LoadScene } from "./LoadScene";
import { deliveryColor, deliverySequences } from "./sceneGeometry";
import "./LoadViewer.css";

/** Passo da animação de carregamento, em ms por volume. */
const STEP_MS = 420;

interface LoadViewerProps {
  readonly planId: string;
}

export function LoadViewer({ planId }: LoadViewerProps) {
  const [view, setView] = useState<LoadPlanVisualization | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showTruck, setShowTruck] = useState(true);

  // OC33: quantos volumes já "entraram" no baú. null = carga completa, sem animar.
  const [step, setStep] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setErrorMessage(null);

    getLoadPlanVisualization(planId)
      .then((loaded) => {
        if (active) setView(loaded);
      })
      .catch((error) => {
        if (!active) return;
        setErrorMessage(
          mapLoadPlanErrorToMessage(
            error instanceof ApiError
              ? error
              : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
          ),
        );
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [planId]);

  const ordered = useMemo(
    () => (view ? [...view.items].sort((a, b) => a.loadingSequence - b.loadingSequence) : []),
    [view],
  );

  // avança a animação enquanto estiver tocando
  useEffect(() => {
    if (!isPlaying || ordered.length === 0) return;

    timer.current = window.setInterval(() => {
      setStep((current) => {
        const next = (current ?? 0) + 1;
        if (next >= ordered.length) {
          setIsPlaying(false);
          return null; // chegou ao fim: volta a mostrar a carga inteira
        }
        return next;
      });
    }, STEP_MS);

    return () => {
      if (timer.current !== null) window.clearInterval(timer.current);
    };
  }, [isPlaying, ordered.length]);

  const visibleIds = useMemo(() => {
    if (step === null) return null;
    return new Set(ordered.slice(0, step).map((item) => item.id));
  }, [ordered, step]);

  const selected: PlacedItem | undefined = ordered.find((item) => item.id === selectedId);

  if (isLoading) {
    return (
      <p className="entity-state">
        <span className="spinner" aria-hidden="true" />
        <span>Carregando visualização…</span>
      </p>
    );
  }

  if (errorMessage) return <AlertBanner>{errorMessage}</AlertBanner>;
  if (!view) return null;

  if (view.items.length === 0) {
    return <p className="entity-state">Nenhum volume foi carregado neste plano, não há o que exibir.</p>;
  }

  return (
    <div className="viewer">
      <div className="viewer-canvas">
        <LoadScene
          truck={view.truck}
          items={ordered}
          selectedId={selectedId}
          onSelect={setSelectedId}
          visibleIds={visibleIds}
          showTruck={showTruck}
        />
      </div>

      <div className="viewer-controls">
        <label className="viewer-toggle" htmlFor="viewer-show-truck">
          <input
            id="viewer-show-truck"
            type="checkbox"
            checked={showTruck}
            onChange={(event) => setShowTruck(event.target.checked)}
          />
          <span>Mostrar caminhão</span>
        </label>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            if (isPlaying) {
              setIsPlaying(false);
              return;
            }
            setStep(0);
            setIsPlaying(true);
          }}
        >
          {isPlaying ? "Pausar" : "Ver carregamento"}
        </button>
        {step !== null ? (
          <>
            <input
              type="range"
              aria-label="Passo do carregamento"
              min={0}
              max={ordered.length}
              value={step}
              onChange={(event) => {
                setIsPlaying(false);
                setStep(Number(event.target.value));
              }}
            />
            <span className="viewer-step">
              {step} de {ordered.length}
            </span>
            <button
              type="button"
              className="btn-link"
              onClick={() => {
                setIsPlaying(false);
                setStep(null);
              }}
            >
              Ver carga completa
            </button>
          </>
        ) : (
          <span className="viewer-hint">
            Arraste para girar, role para aproximar. Clique num volume para ver os detalhes.
          </span>
        )}
      </div>

      <div className="viewer-side">
        <section>
          <h4>Entregas</h4>
          <ul className="viewer-legend">
            {deliverySequences(view.items).map((sequence) => (
              <li key={sequence}>
                <span className="viewer-swatch" style={{ background: deliveryColor(sequence) }} />
                Entrega {sequence}
              </li>
            ))}
          </ul>
          <p className="entity-form-help">
            A cor agrupa por ordem de entrega: quem sai junto na mesma parada tem a mesma cor.
          </p>
        </section>

        {selected ? (
          <section className="viewer-detail">
            <h4>{selected.productCode}</h4>
            <p className="viewer-detail-name">{selected.productName}</p>
            <dl>
              <div>
                <dt>Carregamento</dt>
                <dd>#{selected.loadingSequence}</dd>
              </div>
              <div>
                <dt>Entrega</dt>
                <dd>#{selected.deliverySequence}</dd>
              </div>
              <div>
                <dt>Posição</dt>
                <dd>
                  {selected.xCm}, {selected.yCm}, {selected.zCm} cm
                </dd>
              </div>
              <div>
                <dt>Medidas</dt>
                <dd>
                  {selected.widthCm}×{selected.heightCm}×{selected.lengthCm} cm
                </dd>
              </div>
              <div>
                <dt>Rotação</dt>
                <dd>{ROTATION_LABELS[selected.rotationCode]}</dd>
              </div>
              <div>
                <dt>Peso</dt>
                <dd>{selected.weightKg} kg</dd>
              </div>
            </dl>
          </section>
        ) : null}

        {view.unloadedItems.length > 0 ? (
          <section>
            <h4>Fora da carga ({view.unloadedItems.length})</h4>
            <ul className="viewer-unloaded">
              {view.unloadedItems.map((item) => (
                <li key={item.id}>
                  <strong>{item.productCode}</strong>
                  <span>{REJECTION_LABELS[item.rejectionReason]}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}
