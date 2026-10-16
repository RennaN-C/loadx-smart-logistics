import { Icon } from "../../../components/Icon";
import type { SearchResult } from "../api/searchApi";
import { CATEGORIES } from "./searchPresentation";
import type { SearchStatus } from "./useSearchResults";

const STATUS_TEXT = { idle: "Digite pelo menos 2 caracteres.", loading: "Buscando registros…", error: "Não foi possível pesquisar. Tente novamente." };
interface Props { id: string; results: SearchResult[]; status: SearchStatus; active: number; onActive: (index: number) => void; onChoose: (result: SearchResult) => void; onRetry: () => void }
export function SearchResultsPanel({ id, results, status, active, onActive, onChoose, onRetry }: Readonly<Props>) {
  const feedback = status === "ready" ? (results.length ? `${results.length} resultado(s). Use as setas e Enter para abrir.` : "Nenhum registro encontrado.") : STATUS_TEXT[status];
  return <div className="global-search-panel">
    <div className="global-search-feedback" role="status" aria-live="polite">{feedback}</div>
    {status === "error" ? <button className="global-search-retry" type="button" onClick={onRetry}>Tentar novamente</button> : null}
    <div id={`${id}-results`} role="listbox" aria-label="Resultados da busca" aria-busy={status === "loading"}>
      {Object.entries(CATEGORIES).map(([category, metadata]) => {
        const items = results.map((result, index) => ({ result, index })).filter(({ result }) => result.category === category);
        return items.length ? <div role="group" aria-label={metadata.label} key={category}>
          <p className="global-search-category">{metadata.label}</p>
          {items.map(({ result, index }) => <button key={result.id} type="button" role="option" aria-selected={active === index} tabIndex={-1} id={`${id}-option-${index}`}
            onMouseDown={(event) => event.preventDefault()} onClick={() => onChoose(result)} onMouseEnter={() => onActive(index)}>
            <Icon name={metadata.icon} size={19} /><span>{result.title}</span><Icon name="arrow-right" size={16} />
          </button>)}
        </div> : null;
      })}
    </div>
  </div>;
}
