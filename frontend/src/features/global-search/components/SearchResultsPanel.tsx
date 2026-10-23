import { Icon } from "../../../components/Icon";
import type { SearchResult } from "../api/searchApi";
import { CATEGORIES, searchResultTitle } from "./searchPresentation";
import type { SearchStatus } from "./useSearchResults";

const STATUS_TEXT = { idle: "Digite pelo menos 2 caracteres.", loading: "Buscando registros…", error: "Não foi possível pesquisar. Tente novamente." };
interface Props { id: string; results: SearchResult[]; status: SearchStatus; active: number; onActive: (index: number) => void; onChoose: (result: SearchResult) => void; onRetry: () => void }
export function SearchResultsPanel({ id, results, status, active, onActive, onChoose, onRetry }: Readonly<Props>) {
  let feedback: string;
  if (status === "ready") {
    feedback = results.length ? `${results.length} ${results.length === 1 ? "resultado encontrado" : "resultados encontrados"}.` : "Nenhum registro encontrado.";
  } else {
    feedback = STATUS_TEXT[status];
  }
  return <div className="global-search-panel">
    <div className="global-search-panel-heading"><Icon name="search" size={17} /><span>Resultados da busca</span></div>
    <div className="global-search-feedback" role="status" aria-live="polite">{status === "loading" && <span className="spinner" aria-hidden="true" />}{feedback}</div>
    {status === "ready" && results.length === 0 && <p className="global-search-hint">Confira o termo ou tente outra identificação. A busca respeita o seu acesso aos registros.</p>}
    {status === "error" ? <button className="btn-secondary global-search-retry" type="button" onClick={onRetry}>Tentar novamente</button> : null}
    <div id={`${id}-results`} role="listbox" aria-label="Resultados da busca" aria-busy={status === "loading"}>
      {Object.entries(CATEGORIES).map(([category, metadata]) => {
        const items = results.map((result, index) => ({ result, index })).filter(({ result }) => result.category === category);
        return items.length ? <div role="group" aria-label={metadata.label} key={category}>
          <p className="global-search-category">{metadata.label}</p>
          {items.map(({ result, index }) => <button key={result.id} type="button" role="option" aria-selected={active === index} tabIndex={-1} id={`${id}-option-${index}`}
            onMouseDown={(event) => event.preventDefault()} onClick={() => onChoose(result)} onMouseEnter={() => onActive(index)}>
            <Icon name={metadata.icon} size={19} /><span>{searchResultTitle(result)}</span><Icon name="arrow-right" size={16} />
          </button>)}
        </div> : null;
      })}
    </div>
    <div className="global-search-shortcuts" aria-hidden="true"><span><kbd>↑</kbd><kbd>↓</kbd> Navegar</span><span><kbd>Enter</kbd> Abrir</span><span><kbd>Esc</kbd> Fechar</span></div>
  </div>;
}
