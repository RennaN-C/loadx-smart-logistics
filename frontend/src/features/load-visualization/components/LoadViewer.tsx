import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { getLoadPlanVisualization } from "../../load-planning/api/loadPlansApi";
import { REJECTION_LABELS, ROTATION_LABELS } from "../../load-planning/components/loadPlanLabels";
import { mapLoadPlanErrorToMessage } from "../../load-planning/components/loadPlansErrorMessages";
import type { LoadPlan, LoadPlanVisualization, PlacedItem } from "../../load-planning/types";
import { VIEW_HINTS, VIEW_LABELS, VIEW_PRESETS, type ViewPreset } from "./cameraViews";
import { LoadScene } from "./LoadScene";
import { deliveryColor, deliverySequences } from "./sceneGeometry";
import "./LoadViewer.css";

/** Passo da animação de carregamento, em ms por volume. */
const STEP_MS = 420;

interface LoadViewerProps {
  readonly planId: string;
  /**
   * Métricas prontas, vindas da página. O viewer NÃO recalcula ocupação nem
   * peso: são números que o backend já publicou, e refazer a conta aqui abriria
   * divergência entre o que se lê e o que foi validado (`docs/11`).
   */
  readonly plan: LoadPlan;
}

export function LoadViewer({ planId, plan }: LoadViewerProps) {
  const [view, setView] = useState<LoadPlanVisualization | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showTruck, setShowTruck] = useState(true);
  const [realistic, setRealistic] = useState(true);
  // `view` já é a visualização carregada; este é o ÂNGULO da câmera.
  const [angle, setAngle] = useState<ViewPreset>("isometric");
  const [highlightFragile, setHighlightFragile] = useState(false);

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
          // para no último volume em vez de sumir com o passo a passo: quem
          // chegou ao fim quer ver a carga fechada, não voltar ao começo
          setIsPlaying(false);
          return ordered.length - 1;
        }
        return next;
      });
    }, STEP_MS);

    return () => {
      if (timer.current !== null) window.clearInterval(timer.current);
    };
  }, [isPlaying, ordered.length]);

  /**
   * `step` é o ÍNDICE do volume que está entrando agora, e ele entra no conjunto
   * visível: precisa estar na cena para deslizar até o lugar. Os seguintes ficam
   * esmaecidos, não escondidos, senão o espaço deles pareceria livre.
   */
  const visibleIds = useMemo(() => {
    if (step === null) return null;
    return new Set(ordered.slice(0, step + 1).map((item) => item.id));
  }, [ordered, step]);

  const current = step === null ? null : (ordered[step] ?? null);

  const goTo = useCallback(
    (next: number) => {
      setIsPlaying(false);
      const limite = Math.max(0, Math.min(next, ordered.length - 1));
      setStep(limite);
      // selecionar junto faz o painel lateral já mostrar o volume do passo
      setSelectedId(ordered[limite]?.id ?? null);
    },
    [ordered],
  );

  // ←→ percorrem a sequência. Só enquanto o passo a passo está aberto, para as
  // setas não sequestrarem a rolagem da página no uso normal.
  useEffect(() => {
    if (step === null) return;

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        goTo(step + 1);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        goTo(step - 1);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goTo, step]);

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
      {/* Números do backend, não recalculados aqui. */}
      <div className="viewer-kpis">
        <div className="viewer-kpi">
          <span className="viewer-kpi-label">OCUPAÇÃO</span>
          <span className="viewer-kpi-value">
            {plan.occupancyPercent.toFixed(1)}
            <small>%</small>
          </span>
        </div>
        <div className="viewer-kpi">
          <span className="viewer-kpi-label">PESO EMBARCADO</span>
          <span className="viewer-kpi-value">
            {(plan.totalWeightKg / 1000).toFixed(2)}
            <small>t</small>
          </span>
        </div>
        <div className="viewer-kpi">
          <span className="viewer-kpi-label">VOLUMES</span>
          <span className="viewer-kpi-value">{plan.loadedCount}</span>
        </div>
        <div className={plan.unloadedCount > 0 ? "viewer-kpi viewer-kpi-alert" : "viewer-kpi"}>
          <span className="viewer-kpi-label">FORA DA CARGA</span>
          <span className="viewer-kpi-value">{plan.unloadedCount}</span>
        </div>
      </div>

      <div className="viewer-views" role="group" aria-label="Ângulo da câmera">
        {VIEW_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            className={preset === angle ? "viewer-view is-active" : "viewer-view"}
            aria-pressed={preset === angle}
            title={VIEW_HINTS[preset]}
            onClick={() => setAngle(preset)}
          >
            {VIEW_LABELS[preset]}
          </button>
        ))}
      </div>

      <div className="viewer-canvas">
        <LoadScene
          truck={view.truck}
          items={ordered}
          selectedId={selectedId}
          onSelect={setSelectedId}
          visibleIds={visibleIds}
          showTruck={showTruck}
          realistic={realistic}
          view={angle}
          highlightFragile={highlightFragile}
          enteringId={current?.id ?? null}
        />
      </div>

      <div className="viewer-controls">
        <label className="viewer-toggle" htmlFor="viewer-fragile">
          <input
            id="viewer-fragile"
            type="checkbox"
            checked={highlightFragile}
            onChange={(event) => setHighlightFragile(event.target.checked)}
          />
          <span>Destacar frágeis</span>
        </label>
        <label className="viewer-toggle" htmlFor="viewer-realistic">
          <input
            id="viewer-realistic"
            type="checkbox"
            checked={realistic}
            onChange={(event) => setRealistic(event.target.checked)}
          />
          <span>Realista</span>
        </label>
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
            if (step === null) {
              goTo(0);
              return;
            }
            setStep(null);
            setIsPlaying(false);
          }}
        >
          {step === null ? "Ver carregamento" : "Ver carga completa"}
        </button>

        {step === null ? (
          <span className="viewer-hint">
            Arraste para girar, role para aproximar. Clique num volume para ver os detalhes.
          </span>
        ) : null}
      </div>

      {step !== null && current ? (
        <div className="viewer-stepper">
          <div className="viewer-stepper-nav">
            <button
              type="button"
              className="viewer-step-btn"
              onClick={() => goTo(step - 1)}
              disabled={step === 0}
              aria-label="Volume anterior"
            >
              ◀
            </button>
            <button
              type="button"
              className="viewer-step-btn viewer-step-play"
              onClick={() => {
                if (step >= ordered.length - 1) goTo(0);
                setIsPlaying(!isPlaying);
              }}
            >
              {isPlaying ? "Pausar" : "Tocar"}
            </button>
            <button
              type="button"
              className="viewer-step-btn"
              onClick={() => goTo(step + 1)}
              disabled={step >= ordered.length - 1}
              aria-label="Próximo volume"
            >
              ▶
            </button>
            <span className="viewer-step-count">
              {step + 1} <small>de {ordered.length}</small>
            </span>
          </div>

          <input
            className="viewer-step-range"
            type="range"
            aria-label="Passo do carregamento"
            min={0}
            max={ordered.length - 1}
            value={step}
            onChange={(event) => goTo(Number(event.target.value))}
          />

          <p className="viewer-step-now">
            <strong>{current.productCode}</strong> {current.productName}
            <span>
              {current.widthCm}×{current.heightCm}×{current.lengthCm} cm · entrega #
              {current.deliverySequence}
            </span>
          </p>
          <p className="viewer-step-help">Use ← e → para percorrer a sequência.</p>
        </div>
      ) : null}

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
