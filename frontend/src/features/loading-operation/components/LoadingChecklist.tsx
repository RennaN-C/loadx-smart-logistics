import { StatusPill } from "../../../components/StatusPill";
import type { ChecklistRow } from "../hooks/useLoadingSession";

interface LoadingChecklistProps {
  readonly rows: readonly ChecklistRow[];
  /** Conferência manual liberada: perfil é conferente E sessão em andamento. */
  readonly canCheck: boolean;
  readonly isWorking: boolean;
  readonly onCheck: (itemId: string) => void;
}

/**
 * O checklist do carregamento.
 *
 * A ordem é a de CARREGAMENTO calculada pelo backend, não a de cadastro: é a
 * ordem em que os volumes entram no caminhão, que é como o conferente os
 * encontra na doca.
 *
 * O botão de conferir por item continua existindo ao lado da leitura de
 * código. A OC75 pede os dois: etiqueta rasgada, leitor sem bateria e volume
 * sem código são a razão de o caminho manual não poder sumir.
 */
export function LoadingChecklist({ rows, canCheck, isWorking, onCheck }: LoadingChecklistProps) {
  if (rows.length === 0) {
    return <p className="entity-state">Este carregamento não tem volumes.</p>;
  }

  return (
    <table className="loading-checklist">
      <caption className="sr-only">Volumes do carregamento, na ordem de carregamento</caption>
      <thead>
        <tr>
          <th scope="col">#</th>
          <th scope="col">Produto</th>
          <th scope="col">Situação</th>
          {canCheck ? <th scope="col">Ação</th> : null}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={row.itemId} className={row.checked ? "loading-row-checked" : undefined}>
            <td className="loading-cell-seq">{row.product?.loadingSequence ?? index + 1}</td>
            <td>
              {/* O produto vem do plano. Se faltar, o volume continua conferível
                  — o que não pode é a linha sumir e o checklist mentir sobre
                  quantos volumes existem. */}
              {row.product ? (
                <>
                  <span className="loading-product">{row.product.productName}</span>
                  <span className="loading-code">{row.product.productCode}</span>
                </>
              ) : (
                <span className="loading-product">Volume sem descrição no plano</span>
              )}
            </td>
            <td>
              <StatusPill tone={row.checked ? "good" : "neutral"}>
                {row.checked ? "Conferido" : "Pendente"}
              </StatusPill>
            </td>
            {canCheck ? (
              <td>
                {row.checked ? null : (
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={isWorking}
                    /* Nome próprio por linha: "Conferir" repetido em vinte
                       botões não diz a ninguém QUAL volume será marcado, e
                       ainda colidia com o botão de enviar o código lido. */
                    aria-label={
                      row.product ? `Conferir ${row.product.productName}` : "Conferir volume"
                    }
                    onClick={() => onCheck(row.itemId)}
                  >
                    Conferir
                  </button>
                )}
              </td>
            ) : null}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
