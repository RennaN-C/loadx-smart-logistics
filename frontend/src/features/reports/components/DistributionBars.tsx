import type { Slice } from "../reportMetrics";

const percent = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 0 });

interface DistributionBarsProps {
  readonly slices: readonly Slice[];
  /** Rótulo legível da chave; a chave crua é o fallback. */
  readonly label: (key: string) => string;
  /** Tom da barra por chave, quando a cor carrega significado. */
  readonly tone?: (key: string) => "accent" | "muted" | "good";
}

const TONE_CLASS = {
  accent: "report-bar-fill",
  muted: "report-bar-fill report-bar-fill-muted",
  good: "report-bar-fill report-bar-fill-good",
} as const;

export function DistributionBars({ slices, label, tone }: DistributionBarsProps) {
  return (
    <ul className="report-bars">
      {slices.map((slice) => (
        <li key={slice.key}>
          <div className="report-bar-head">
            <span>{label(slice.key)}</span>
            <span>
              <span className="report-bar-count">{slice.count}</span>
              <span className="report-bar-share">{percent.format(slice.share)}</span>
            </span>
          </div>
          {/* a barra repete o número ao lado, então não precisa ser lida de novo */}
          <div className="report-bar-track" aria-hidden="true">
            <div
              className={TONE_CLASS[tone?.(slice.key) ?? "accent"]}
              style={{ width: `${slice.share * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
