/**
 * Ilustração do baú com as cotas do cadastro.
 *
 * As imagens são fixas: não deformam conforme as medidas digitadas. O que muda
 * é só o valor das cotas ao lado do desenho. Isso é decisão de produto — o
 * desenho serve para situar quem cadastra, e o número é que carrega a informação.
 */

const TRUCK_IMAGES = {
  side: "/trucks/truck-side.png",
  rear: "/trucks/truck-rear.png",
} as const;

export interface TruckDimensions {
  readonly widthCm: number;
  readonly heightCm: number;
  readonly lengthCm: number;
}

export type SchematicVariant = "card" | "detailed";

/** Enquanto a medida não foi digitada, mostra um traço em vez de "0 cm". */
function formatCm(value: number): string {
  return value > 0 ? `${value} cm` : "—";
}

interface DimensionProps {
  readonly value: number;
  readonly caption: string;
}

function DimensionH({ value, caption }: DimensionProps) {
  return (
    <div className="dim dim-h">
      <span className="dim-line" aria-hidden="true" />
      <span className="dim-value">{formatCm(value)}</span>
      <span className="dim-caption">{caption}</span>
    </div>
  );
}

function DimensionV({ value, caption }: DimensionProps) {
  return (
    <div className="dim dim-v">
      <span className="dim-line" aria-hidden="true" />
      <span className="dim-text">
        <span className="dim-value">{formatCm(value)}</span>
        <span className="dim-caption">{caption}</span>
      </span>
    </div>
  );
}

export interface TruckSchematicProps {
  readonly dimensions: TruckDimensions;
  readonly view: "side" | "rear";
  readonly variant: SchematicVariant;
}

export function TruckSchematic({ dimensions, view, variant }: TruckSchematicProps) {
  // decorativa: a informação real está nas cotas, que são texto de verdade
  const image = <img className="truck-photo" src={TRUCK_IMAGES[view]} alt="" />;

  if (variant === "card") {
    return <div className="truck-photo-card">{image}</div>;
  }

  if (view === "rear") {
    return (
      <figure className="truck-figure truck-figure-rear">
        <p className="truck-figure-label">TRASEIRA</p>
        <div className="truck-figure-image">{image}</div>
        <DimensionH value={dimensions.widthCm} caption="LARGURA" />
      </figure>
    );
  }

  return (
    <figure className="truck-figure truck-figure-side">
      <p className="truck-figure-label">VISTA LATERAL</p>
      <div className="truck-figure-image">{image}</div>
      <DimensionV value={dimensions.heightCm} caption="ALTURA INTERNA" />
      <DimensionH value={dimensions.lengthCm} caption="COMPRIMENTO" />
    </figure>
  );
}
