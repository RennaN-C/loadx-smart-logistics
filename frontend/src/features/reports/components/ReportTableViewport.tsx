import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Icon } from "../../../components/Icon";

/** Controles nativos tornam colunas fora da tela acessíveis por teclado e toque. */
export function ReportTableViewport({ label, children }: { readonly label: string; readonly children: ReactNode }) {
  const id = useId();
  const viewport = useRef<HTMLElement>(null);
  const [range, setRange] = useState({ left: 0, max: 0 });
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const update = () => setRange({ left: element.scrollLeft, max: Math.max(0, element.scrollWidth - element.clientWidth) });
    update();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(update);
    observer?.observe(element);
    element.addEventListener("scroll", update);
    window.addEventListener("resize", update);
    return () => { observer?.disconnect(); element.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, []);
  function scroll(left: number) { viewport.current?.scrollBy({ left, behavior: "auto" }); }
  return <>
    <section ref={viewport} id={id} className="report-table-scroll" aria-label={label}>{children}</section>
    {range.max > 0 && <fieldset className="report-scroll-controls"><legend className="sr-only">Rolagem — {label}</legend>
      <button type="button" className="btn-secondary report-scroll-back" aria-controls={id} disabled={range.left <= 0} onClick={() => scroll(-240)}><Icon name="arrow-right" size={16} />Colunas anteriores</button>
      <button type="button" className="btn-secondary" aria-controls={id} disabled={range.left >= range.max - 1} onClick={() => scroll(240)}>Próximas colunas<Icon name="arrow-right" size={16} /></button>
    </fieldset>}
  </>;
}
