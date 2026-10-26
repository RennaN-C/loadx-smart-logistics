import { useId } from "react";

export interface ChartEntry { readonly label: string; readonly value: number }

/** Geometry scales the supplied counts; it does not publish derived metrics. */
export function DistributionChart({ title, total, entries, period = "desde o início", variant = "ring" }: {
  readonly title: string;
  readonly total: number;
  readonly entries: readonly ChartEntry[];
  readonly period?: string;
  readonly variant?: "ring" | "columns";
}) {
  const heading = useId();
  let offset = 0;
  const segments = entries.map((entry) => {
    const segment = { ...entry, offset };
    offset += entry.value;
    return segment;
  });
  const scale = Math.max(total, 1);
  return <figure className="distribution-chart" aria-labelledby={heading}>
    <figcaption id={heading}><h3>{title}</h3><p>Contagens da consulta · {period}</p></figcaption>
    <div className="distribution-chart-body">
      {variant === "ring" ? <div className="distribution-ring">
        <svg viewBox="0 0 180 180" role="img" aria-label={`${title}: ${total} registros`}>
          <circle cx="90" cy="90" r="66" className="distribution-track" />
          {total > 0 ? segments.map((entry, index) => <circle key={entry.label} cx="90" cy="90" r="66" pathLength={scale} strokeDasharray={`${entry.value} ${scale - entry.value}`} strokeDashoffset={-entry.offset} transform="rotate(-90 90 90)" className={`chart-color-${index % 4}`}><title>{entry.label}: {entry.value}</title></circle>) : null}
          <text x="90" y="90" textAnchor="middle" className="distribution-total">{total}</text><text x="90" y="110" textAnchor="middle" className="distribution-unit">registros</text>
        </svg>
      </div> : <svg className="distribution-columns" viewBox="0 0 320 180" role="img" aria-label={`${title}: ${total} registros`}>
        {[35, 75, 115, 155].map((y) => <line key={y} x1="20" x2="310" y1={y} y2={y} className="distribution-gridline" />)}
        {entries.map((entry, index) => {
          const height = entry.value / scale * 130;
          const width = 270 / Math.max(entries.length, 1);
          return <g key={entry.label}><rect x={30 + index * width} y={155 - height} width={width * .55} height={height} rx="4" className={`chart-color-${index % 4}`} /><text x={30 + index * width + width * .275} y={146 - height} textAnchor="middle" className="distribution-bar-value">{entry.value}</text><title>{entry.label}: {entry.value}</title></g>;
        })}
      </svg>}
      <ul className="distribution-legend">{entries.map((entry, index) => <li key={entry.label}><span className={`chart-dot chart-color-${index % 4}`} aria-hidden="true" /><span>{entry.label}</span><strong>{entry.value}</strong></li>)}</ul>
    </div>
    {total === 0 ? <p className="distribution-empty">Sem registros nesta consulta.</p> : null}
  </figure>;
}
