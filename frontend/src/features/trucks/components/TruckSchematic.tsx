import { useId } from "react";

import {
  computeRearLayout,
  computeSideLayout,
  type RearLayout,
  type SchematicVariant,
  type SideLayout,
  type TruckDimensions,
} from "./truckGeometry";

interface GradientDefsProps {
  readonly uid: string;
}

function GradientDefs({ uid }: GradientDefsProps) {
  return (
    <defs>
      <linearGradient id={`panel-${uid}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="var(--card)" />
        <stop offset="1" stopColor="var(--paper)" />
      </linearGradient>
      <linearGradient id={`cab-${uid}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="var(--accent)" />
        <stop offset="1" stopColor="var(--accent)" stopOpacity="0.78" />
      </linearGradient>
      <linearGradient id={`tyre-${uid}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="var(--muted)" />
        <stop offset="1" stopColor="var(--ink)" />
      </linearGradient>
    </defs>
  );
}

interface WheelProps {
  readonly cx: number;
  readonly groundY: number;
  readonly radius: number;
  readonly uid: string;
  readonly detailed: boolean;
}

/** O pneu toca o chão: o centro fica em `groundY - radius`, nunca sobre a linha. */
function Wheel({ cx, groundY, radius, uid, detailed }: WheelProps) {
  const cy = groundY - radius;
  const studs = detailed
    ? Array.from({ length: 6 }, (_, index) => {
        const angle = (Math.PI * 2 * index) / 6 - Math.PI / 2;
        return {
          key: index,
          cx: cx + Math.cos(angle) * radius * 0.34,
          cy: cy + Math.sin(angle) * radius * 0.34,
        };
      })
    : [];

  return (
    <g>
      <circle cx={cx} cy={cy} r={radius} fill={`url(#tyre-${uid})`} stroke="var(--ink)" strokeWidth="1" />
      <circle cx={cx} cy={cy} r={radius * 0.52} fill="var(--card)" stroke="var(--muted)" strokeWidth="1" />
      <circle cx={cx} cy={cy} r={radius * 0.16} fill="var(--muted)" />
      {studs.map((stud) => (
        <circle key={stud.key} cx={stud.cx} cy={stud.cy} r={Math.max(radius * 0.055, 0.5)} fill="var(--muted)" />
      ))}
    </g>
  );
}

/** Rodado duplo visto de lado: o pneu interno aparece só um pouco atrás do externo. */
function DualWheel({ cx, groundY, radius, uid, detailed }: WheelProps) {
  const offset = radius * 0.55;

  return (
    <g>
      <Wheel cx={cx - offset} groundY={groundY} radius={radius} uid={uid} detailed={false} />
      <Wheel cx={cx + offset} groundY={groundY} radius={radius} uid={uid} detailed={detailed} />
    </g>
  );
}

interface CabProps {
  readonly layout: SideLayout;
  readonly uid: string;
  readonly detailed: boolean;
}

/** Cabine avançada (cab-over), o padrão dos caminhões com baú no Brasil. */
function Cab({ layout, uid, detailed }: CabProps) {
  const { cabLeft, cabTop, cabWidth, cabHeight } = layout;
  const x = (fraction: number) => cabLeft + fraction * cabWidth;
  const y = (fraction: number) => cabTop + fraction * cabHeight;
  const points = (pairs: readonly (readonly [number, number])[]) =>
    pairs.map(([fx, fy]) => `${x(fx).toFixed(1)},${y(fy).toFixed(1)}`).join(" ");

  return (
    <g>
      {detailed ? (
        <rect
          x={x(1)}
          y={y(-0.16)}
          width={cabWidth * 0.05}
          height={cabHeight}
          rx="1.5"
          fill="var(--muted)"
          stroke="var(--ink)"
          strokeWidth="0.8"
        />
      ) : null}

      <polygon
        points={points([
          [0.07, 1],
          [0, 0.9],
          [0, 0.5],
          [0.05, 0.24],
          [0.16, 0.09],
          [0.3, 0.03],
          [1, 0.03],
          [1, 1],
        ])}
        fill={`url(#cab-${uid})`}
        stroke="var(--ink)"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <polygon
        points={points([
          [0.09, 0.31],
          [0.19, 0.13],
          [0.31, 0.13],
          [0.23, 0.33],
        ])}
        fill="var(--ink)"
        opacity="0.55"
      />
      <rect
        x={x(0.37)}
        y={y(0.13)}
        width={cabWidth * 0.5}
        height={cabHeight * 0.25}
        rx="1.5"
        fill="var(--ink)"
        opacity="0.4"
      />
      <line x1={x(0.34)} y1={y(0.07)} x2={x(0.34)} y2={y(0.92)} stroke="var(--ink)" strokeWidth="1" opacity="0.45" />
      <rect
        x={x(-0.02)}
        y={y(0.84)}
        width={cabWidth * 0.15}
        height={cabHeight * 0.15}
        rx="1"
        fill="var(--muted)"
        stroke="var(--ink)"
        strokeWidth="0.8"
      />
      <rect
        x={x(0.01)}
        y={y(0.66)}
        width={cabWidth * 0.09}
        height={cabHeight * 0.1}
        rx="1"
        fill="var(--card)"
        stroke="var(--muted)"
        strokeWidth="1"
      />

      {detailed ? (
        <>
          <line x1={x(0.16)} y1={y(0.17)} x2={x(0.06)} y2={y(0.12)} stroke="var(--ink)" strokeWidth="1.4" />
          <rect
            x={x(0.01)}
            y={y(0.08)}
            width={cabWidth * 0.06}
            height={cabHeight * 0.12}
            rx="1"
            fill="var(--muted)"
            stroke="var(--ink)"
            strokeWidth="0.8"
          />
          <rect
            x={x(0.68)}
            y={y(0.45)}
            width={cabWidth * 0.1}
            height={cabHeight * 0.035}
            rx="1"
            fill="var(--ink)"
            opacity="0.45"
          />
          <rect
            x={x(0.4)}
            y={y(0.93)}
            width={cabWidth * 0.24}
            height={cabHeight * 0.05}
            rx="1"
            fill="var(--ink)"
            opacity="0.42"
          />
          {[0.5, 0.57].map((fy) => (
            <line key={fy} x1={x(0.02)} y1={y(fy)} x2={x(0.13)} y2={y(fy)} stroke="var(--ink)" strokeWidth="1" opacity="0.35" />
          ))}
        </>
      ) : null}
    </g>
  );
}

interface BoxSideProps {
  readonly layout: SideLayout;
  readonly uid: string;
  readonly detailed: boolean;
}

function BoxSide({ layout, uid, detailed }: BoxSideProps) {
  const { boxLeft, boxRight, boxTop, boxWidth, boxHeight } = layout;
  const bottom = boxTop + boxHeight;
  const railHeight = Math.max(boxHeight * 0.07, 1.8);
  const doorWidth = Math.max(boxWidth * 0.05, 3.5);
  const doorX = boxRight - doorWidth;
  const frontPost = Math.max(boxWidth * 0.022, 1.6);
  const hingeWidth = Math.max(doorWidth * 0.62, 2.2);
  const hingeHeight = Math.max(boxHeight * 0.08, 2.4);

  const ribSpan = doorX - (boxLeft + frontPost);
  const ribCount = Math.max(Math.round(ribSpan / 15), 3);
  const ribs = detailed
    ? Array.from({ length: ribCount - 1 }, (_, index) => boxLeft + frontPost + (ribSpan * (index + 1)) / ribCount)
    : [];

  const tapeY = bottom - railHeight - Math.max(boxHeight * 0.05, 1.8);
  const tapeHeight = Math.max(boxHeight * 0.03, 1.2);

  return (
    <g>
      <rect
        x={boxLeft}
        y={boxTop}
        width={boxWidth}
        height={boxHeight}
        fill={`url(#panel-${uid})`}
        stroke="var(--ink)"
        strokeWidth="1.6"
      />

      {ribs.map((rx) => (
        <line key={rx} x1={rx} y1={boxTop + railHeight} x2={rx} y2={bottom - railHeight} stroke="var(--line)" strokeWidth="0.9" opacity="0.55" />
      ))}

      <rect x={boxLeft} y={boxTop} width={boxWidth} height={railHeight} fill="var(--line)" />
      <rect x={boxLeft} y={bottom - railHeight} width={boxWidth} height={railHeight} fill="var(--muted)" opacity="0.42" />
      <line
        x1={boxLeft + frontPost}
        y1={boxTop + railHeight}
        x2={boxLeft + frontPost}
        y2={bottom - railHeight}
        stroke="var(--line)"
        strokeWidth="1.1"
      />
      <rect
        x={boxLeft + frontPost}
        y={boxTop + railHeight + boxHeight * 0.11}
        width={doorX - boxLeft - frontPost}
        height={Math.max(boxHeight * 0.035, 1.3)}
        fill="var(--accent)"
        opacity="0.85"
      />

      <rect x={doorX} y={boxTop} width={doorWidth} height={boxHeight} fill="var(--line)" opacity="0.55" />
      <line x1={doorX} y1={boxTop} x2={doorX} y2={bottom} stroke="var(--ink)" strokeWidth="1.3" />
      {[0.2, 0.5, 0.8].map((fy) => (
        <rect
          key={fy}
          x={boxRight - hingeWidth}
          y={boxTop + boxHeight * fy - hingeHeight / 2}
          width={hingeWidth}
          height={hingeHeight}
          rx="0.8"
          fill="var(--ink)"
          opacity="0.6"
        />
      ))}

      {detailed
        ? [0.07, 0.62].map((fx) => (
            <rect key={fx} x={boxLeft + boxWidth * fx} y={tapeY} width={boxWidth * 0.24} height={tapeHeight} fill="var(--accent)" opacity="0.65" />
          ))
        : null}
    </g>
  );
}

interface BoxRearProps {
  readonly layout: RearLayout;
  readonly uid: string;
  readonly detailed: boolean;
}

/** Traseira: as duas folhas da porta, com barras de travamento e dobradiças. */
function BoxRear({ layout, uid, detailed }: BoxRearProps) {
  const { boxLeft, boxRight, boxTop, boxWidth, boxHeight } = layout;
  const bottom = boxTop + boxHeight;
  const midX = boxLeft + boxWidth / 2;
  const railHeight = Math.max(boxHeight * 0.07, 1.8);
  const inset = Math.max(boxWidth * 0.05, 2);
  const leafTop = boxTop + railHeight + inset * 0.4;
  const leafHeight = bottom - leafTop - inset * 0.4;
  const leafWidth = midX - boxLeft - inset * 1.3;
  const hingeWidth = Math.max(boxWidth * 0.035, 2);
  const hingeHeight = Math.max(boxHeight * 0.07, 2.2);

  return (
    <g>
      <rect
        x={boxLeft}
        y={boxTop}
        width={boxWidth}
        height={boxHeight}
        fill={`url(#panel-${uid})`}
        stroke="var(--ink)"
        strokeWidth="1.6"
      />
      <rect x={boxLeft} y={boxTop} width={boxWidth} height={railHeight} fill="var(--line)" />

      <rect x={boxLeft + inset} y={leafTop} width={leafWidth} height={leafHeight} fill="none" stroke="var(--line)" strokeWidth="1.1" />
      <rect x={midX + inset * 0.3} y={leafTop} width={leafWidth} height={leafHeight} fill="none" stroke="var(--line)" strokeWidth="1.1" />
      <line x1={midX} y1={boxTop + railHeight} x2={midX} y2={bottom} stroke="var(--ink)" strokeWidth="1.5" />

      {[-1, 1].map((direction) => {
        const rodX = midX + direction * boxWidth * 0.085;
        return (
          <g key={direction}>
            <line x1={rodX} y1={leafTop + inset * 0.5} x2={rodX} y2={bottom - inset * 0.5} stroke="var(--muted)" strokeWidth="1.2" />
            <rect
              x={rodX - Math.max(boxWidth * 0.018, 1.2)}
              y={boxTop + boxHeight * 0.52}
              width={Math.max(boxWidth * 0.036, 2.4)}
              height={Math.max(boxHeight * 0.07, 2.6)}
              rx="1"
              fill="var(--ink)"
              opacity="0.55"
            />
          </g>
        );
      })}

      {[0.22, 0.52, 0.82].map((fy) => (
        <g key={fy}>
          <rect x={boxLeft} y={boxTop + boxHeight * fy - hingeHeight / 2} width={hingeWidth} height={hingeHeight} rx="0.8" fill="var(--ink)" opacity="0.55" />
          <rect x={boxRight - hingeWidth} y={boxTop + boxHeight * fy - hingeHeight / 2} width={hingeWidth} height={hingeHeight} rx="0.8" fill="var(--ink)" opacity="0.55" />
        </g>
      ))}

      <rect
        x={boxLeft + inset}
        y={boxTop + railHeight + boxHeight * 0.11}
        width={boxWidth - inset * 2}
        height={Math.max(boxHeight * 0.035, 1.3)}
        fill="var(--accent)"
        opacity="0.85"
      />

      {detailed ? (
        <>
          <rect x={boxLeft + inset} y={bottom - Math.max(boxHeight * 0.075, 2.6)} width={boxWidth * 0.3} height={Math.max(boxHeight * 0.03, 1.2)} fill="var(--accent)" opacity="0.65" />
          <rect
            x={boxRight - inset - boxWidth * 0.3}
            y={bottom - Math.max(boxHeight * 0.075, 2.6)}
            width={boxWidth * 0.3}
            height={Math.max(boxHeight * 0.03, 1.2)}
            fill="var(--accent)"
            opacity="0.65"
          />
          {[0.12, 0.88].map((fx) => (
            <rect
              key={fx}
              x={boxLeft + boxWidth * fx - boxWidth * 0.035}
              y={bottom - Math.max(boxHeight * 0.2, 7)}
              width={boxWidth * 0.07}
              height={Math.max(boxHeight * 0.06, 2.4)}
              rx="1"
              fill="var(--danger)"
              opacity="0.55"
            />
          ))}
        </>
      ) : null}
    </g>
  );
}

interface DimensionLineHProps {
  readonly x1: number;
  readonly x2: number;
  readonly y: number;
}

function DimensionLineH({ x1, x2, y }: DimensionLineHProps) {
  return (
    <g stroke="var(--accent)" strokeWidth="1">
      <line x1={x1} y1={y} x2={x2} y2={y} />
      <line x1={x1} y1={y - 4} x2={x1} y2={y + 4} />
      <line x1={x2} y1={y - 4} x2={x2} y2={y + 4} />
    </g>
  );
}

interface DimensionLineVProps {
  readonly x: number;
  readonly y1: number;
  readonly y2: number;
}

function DimensionLineV({ x, y1, y2 }: DimensionLineVProps) {
  return (
    <g stroke="var(--accent)" strokeWidth="1">
      <line x1={x} y1={y1} x2={x} y2={y2} />
      <line x1={x - 4} y1={y1} x2={x + 4} y2={y1} />
      <line x1={x - 4} y1={y2} x2={x + 4} y2={y2} />
    </g>
  );
}

interface CalloutProps {
  readonly x: number;
  readonly y: number;
  readonly value: string;
  readonly caption: string;
}

function Callout({ x, y, value, caption }: CalloutProps) {
  return (
    <>
      <text x={x} y={y} className="schematic-value" textAnchor="middle">
        {value}
      </text>
      <text x={x} y={y + 11} className="schematic-caption" textAnchor="middle">
        {caption}
      </text>
    </>
  );
}

export interface TruckSchematicProps {
  readonly dimensions: TruckDimensions;
  readonly view: "side" | "rear";
  readonly variant: SchematicVariant;
}

export function TruckSchematic({ dimensions, view, variant }: TruckSchematicProps) {
  const uid = useId().replace(/:/g, "");
  const detailed = variant === "detailed";

  if (view === "rear") {
    const layout = computeRearLayout(dimensions, variant);
    const { boxLeft, boxRight, boxWidth, deckY, groundY, railHeight, viewWidth, viewHeight, wheelRadius } = layout;
    const barY = groundY - wheelRadius * 0.85;

    return (
      <svg viewBox={`0 0 ${viewWidth} ${viewHeight}`} className="truck-schematic" aria-hidden="true">
        <GradientDefs uid={uid} />
        <ellipse cx={viewWidth / 2} cy={groundY + 1.5} rx={boxWidth * 0.62} ry={detailed ? 3.5 : 2} fill="var(--ink)" opacity="0.08" />
        <line x1="4" y1={groundY} x2={viewWidth - 4} y2={groundY} stroke="var(--muted)" strokeWidth="1.2" />

        <Wheel cx={layout.leftAxleX} groundY={groundY} radius={wheelRadius} uid={uid} detailed={detailed} />
        <Wheel cx={layout.rightAxleX} groundY={groundY} radius={wheelRadius} uid={uid} detailed={detailed} />
        <rect x={boxLeft + boxWidth * 0.1} y={deckY} width={boxWidth * 0.8} height={railHeight} fill="var(--ink)" opacity="0.5" />

        <BoxRear layout={layout} uid={uid} detailed={detailed} />

        {detailed ? (
          <>
            {[0.28, 0.72].map((fx) => (
              <line key={fx} x1={boxLeft + boxWidth * fx} y1={deckY + railHeight} x2={boxLeft + boxWidth * fx} y2={barY} stroke="var(--muted)" strokeWidth="1.4" />
            ))}
            <rect x={boxLeft + boxWidth * 0.16} y={barY} width={boxWidth * 0.68} height={Math.max(wheelRadius * 0.2, 1.6)} rx="0.8" fill="var(--muted)" />
            <DimensionLineH x1={boxLeft} x2={boxRight} y={groundY + 15} />
            <Callout x={viewWidth / 2} y={groundY + 32} value={`${dimensions.widthCm} cm`} caption="LARGURA" />
            <text x={viewWidth / 2} y="12" className="schematic-label" textAnchor="middle">
              TRASEIRA
            </text>
          </>
        ) : null}
      </svg>
    );
  }

  const layout = computeSideLayout(dimensions, variant);
  const { boxLeft, boxRight, boxTop, boxWidth, boxHeight, cabLeft, cabTop, cabWidth, cabHeight } = layout;
  const { deckY, groundY, railHeight, viewWidth, viewHeight, wheelRadius, rearAxleX, frontAxleX } = layout;
  const barY = groundY - wheelRadius * 0.85;
  const fenderY = groundY - wheelRadius * 1.9;
  const fenderR = wheelRadius * 1.05;

  return (
    <svg viewBox={`0 0 ${viewWidth} ${viewHeight}`} className="truck-schematic" aria-hidden="true">
      <GradientDefs uid={uid} />
      <ellipse
        cx={(cabLeft + boxRight) / 2}
        cy={groundY + 1.5}
        rx={(boxRight - cabLeft) * 0.5}
        ry={detailed ? 3.5 : 2}
        fill="var(--ink)"
        opacity="0.08"
      />
      <line x1={Math.max(cabLeft - 10, 2)} y1={groundY} x2={boxRight + 8} y2={groundY} stroke="var(--muted)" strokeWidth="1.2" />

      <rect x={cabLeft + cabWidth * 0.4} y={deckY} width={boxRight - cabLeft - cabWidth * 0.4} height={railHeight} fill="var(--ink)" opacity="0.5" />

      {detailed ? (
        <>
          {[0.055, 0.14].map((fx) => (
            <line key={fx} x1={boxRight - boxWidth * fx} y1={deckY + railHeight} x2={boxRight - boxWidth * fx} y2={barY} stroke="var(--muted)" strokeWidth="1.4" />
          ))}
          <rect x={boxRight - boxWidth * 0.19} y={barY} width={boxWidth * 0.19} height={Math.max(wheelRadius * 0.2, 1.6)} rx="0.8" fill="var(--muted)" />
          <rect x={rearAxleX + wheelRadius * 1.35} y={deckY + railHeight} width={Math.max(wheelRadius * 0.2, 1.4)} height={wheelRadius * 1.15} fill="var(--ink)" opacity="0.45" />
        </>
      ) : null}

      <BoxSide layout={layout} uid={uid} detailed={detailed} />
      <Cab layout={layout} uid={uid} detailed={detailed} />

      {detailed ? (
        <polygon
          points={`${cabLeft + cabWidth * 0.45},${cabTop + cabHeight * 0.03} ${boxLeft},${boxTop + boxHeight * 0.28} ${boxLeft},${cabTop + cabHeight * 0.03}`}
          fill="var(--accent)"
          opacity="0.55"
          stroke="var(--ink)"
          strokeWidth="1"
        />
      ) : null}

      <Wheel cx={frontAxleX} groundY={groundY} radius={wheelRadius * 0.92} uid={uid} detailed={detailed} />
      <path
        d={`M ${frontAxleX - fenderR * 1.35} ${fenderY} A ${fenderR * 1.35} ${fenderR * 1.1} 0 0 1 ${frontAxleX + fenderR * 1.35} ${fenderY}`}
        fill="none"
        stroke="var(--ink)"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity="0.5"
      />
      {detailed ? (
        <DualWheel cx={rearAxleX} groundY={groundY} radius={wheelRadius} uid={uid} detailed />
      ) : (
        <Wheel cx={rearAxleX} groundY={groundY} radius={wheelRadius} uid={uid} detailed={false} />
      )}

      {detailed ? (
        <>
          <DimensionLineH x1={boxLeft} x2={boxRight} y={groundY + 15} />
          <Callout x={boxLeft + boxWidth / 2} y={groundY + 32} value={`${dimensions.lengthCm} cm`} caption="COMPRIMENTO" />
          <DimensionLineV x={boxRight + 18} y1={boxTop} y2={deckY} />
          <Callout x={boxRight + 50} y={(boxTop + deckY) / 2 - 4} value={`${dimensions.heightCm} cm`} caption="ALTURA INTERNA" />
          <text x={boxLeft + boxWidth / 2} y="12" className="schematic-label" textAnchor="middle">
            VISTA LATERAL
          </text>
        </>
      ) : null}
    </svg>
  );
}
