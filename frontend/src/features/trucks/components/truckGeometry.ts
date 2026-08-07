/**
 * Geometria do desenho técnico do caminhão.
 *
 * O baú é desenhado proporcional às medidas reais informadas no cadastro: a mesma
 * altura em cm sempre vira a mesma altura em px, dentro dos limites da viewBox.
 * O piso do baú fica apoiado no chassi, acima do topo dos pneus — por isso `deckY`
 * (piso) e `groundY` (chão) são coordenadas distintas.
 */

export type SchematicVariant = "card" | "detailed";

export interface TruckDimensions {
  readonly widthCm: number;
  readonly heightCm: number;
  readonly lengthCm: number;
}

interface BaseLayout {
  readonly viewWidth: number;
  readonly viewHeight: number;
  readonly groundY: number;
  readonly deckY: number;
  readonly railHeight: number;
  readonly wheelRadius: number;
  readonly boxLeft: number;
  readonly boxRight: number;
  readonly boxTop: number;
  readonly boxWidth: number;
  readonly boxHeight: number;
}

export interface SideLayout extends BaseLayout {
  readonly cabLeft: number;
  readonly cabTop: number;
  readonly cabWidth: number;
  readonly cabHeight: number;
  readonly frontAxleX: number;
  readonly rearAxleX: number;
}

export interface RearLayout extends BaseLayout {
  readonly leftAxleX: number;
  readonly rightAxleX: number;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Escala em px/cm, limitada para o desenho nunca estourar a viewBox. */
function resolveScale(
  detailed: boolean,
  spanCm: number,
  heightCm: number,
  maxSpanPx: number,
  maxHeightPx: number,
): number {
  return Math.min(
    detailed ? 0.22 : 0.095,
    maxSpanPx / Math.max(spanCm, 1),
    maxHeightPx / Math.max(heightCm, 1),
  );
}

export function computeSideLayout(dimensions: TruckDimensions, variant: SchematicVariant): SideLayout {
  const detailed = variant === "detailed";
  const viewWidth = detailed ? 420 : 148;
  const viewHeight = detailed ? 210 : 68;
  const groundY = viewHeight - (detailed ? 46 : 12);
  const wheelRadius = detailed ? 13 : 5.4;
  const deckY = groundY - wheelRadius * 2.2;
  const railHeight = Math.max(wheelRadius * 0.3, 1.8);

  const scale = resolveScale(
    detailed,
    dimensions.lengthCm,
    dimensions.heightCm,
    detailed ? 205 : 86,
    deckY - (detailed ? 24 : 6),
  );
  const boxWidth = Math.max(dimensions.lengthCm * scale, detailed ? 78 : 32);
  const boxHeight = Math.max(dimensions.heightCm * scale, detailed ? 42 : 17);
  const boxTop = deckY - boxHeight;

  const cabWidth = wheelRadius * (detailed ? 5.4 : 5);
  const cabHeight = clamp(boxHeight * 0.8, wheelRadius * 3.3, wheelRadius * 5);
  const cabTop = groundY - wheelRadius * 1.05 - cabHeight;

  const gap = wheelRadius * 0.22;
  const cabLeft = detailed ? 18 : Math.max((viewWidth - (cabWidth + gap + boxWidth)) / 2, 4);
  const boxLeft = cabLeft + cabWidth + gap;

  return {
    viewWidth,
    viewHeight,
    groundY,
    deckY,
    railHeight,
    wheelRadius,
    boxLeft,
    boxRight: boxLeft + boxWidth,
    boxTop,
    boxWidth,
    boxHeight,
    cabLeft,
    cabTop,
    cabWidth,
    cabHeight,
    frontAxleX: cabLeft + cabWidth * 0.55,
    // eixo traseiro no fim do baú, deixando o balanço traseiro visível
    rearAxleX: boxLeft + boxWidth * 0.76,
  };
}

export function computeRearLayout(dimensions: TruckDimensions, variant: SchematicVariant): RearLayout {
  const detailed = variant === "detailed";
  const viewWidth = detailed ? 150 : 78;
  const viewHeight = detailed ? 210 : 68;
  const groundY = viewHeight - (detailed ? 46 : 12);
  const wheelRadius = detailed ? 11 : 4.6;
  const deckY = groundY - wheelRadius * 2.2;
  const railHeight = Math.max(wheelRadius * 0.3, 1.8);

  const scale = resolveScale(
    detailed,
    dimensions.widthCm,
    dimensions.heightCm,
    detailed ? 100 : 52,
    deckY - (detailed ? 24 : 6),
  );
  const boxWidth = Math.max(dimensions.widthCm * scale, detailed ? 50 : 22);
  const boxHeight = Math.max(dimensions.heightCm * scale, detailed ? 42 : 17);
  const boxLeft = (viewWidth - boxWidth) / 2;

  return {
    viewWidth,
    viewHeight,
    groundY,
    deckY,
    railHeight,
    wheelRadius,
    boxLeft,
    boxRight: boxLeft + boxWidth,
    boxTop: deckY - boxHeight,
    boxWidth,
    boxHeight,
    leftAxleX: boxLeft + boxWidth * 0.16,
    rightAxleX: boxLeft + boxWidth * 0.84,
  };
}
