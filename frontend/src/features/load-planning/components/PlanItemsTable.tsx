import type { LoadPlanItem } from "../types";
import { REJECTION_LABELS, ROTATION_LABELS } from "./loadPlanLabels";

interface PlanItemsTableProps {
  readonly items: readonly LoadPlanItem[];
}

/**
 * Duas tabelas, não uma com coluna de situação: quem carrega o caminhão lê a
 * sequência de carregamento, e quem resolve pendência lê os motivos. Misturar
 * as duas leituras atrapalha as duas.
 */
export function PlanItemsTable({ items }: PlanItemsTableProps) {
  const loaded = items
    .filter((item) => item.placed)
    .sort((a, b) => (a.loadingSequence ?? 0) - (b.loadingSequence ?? 0));
  const rejected = items.filter((item) => !item.placed);

  return (
    <>
      <section className="plan-table-block">
        <h3>Sequência de carregamento</h3>
        <p className="entity-form-help">
          Carregue nesta ordem. O item 1 entra primeiro, no fundo do baú; a última entrega sai primeiro.
        </p>
        <div className="plan-table-scroll">
          <table className="plan-table">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Produto</th>
                <th scope="col">Posição (x, y, z)</th>
                <th scope="col">Medidas</th>
                <th scope="col">Rotação</th>
                <th scope="col">Entrega</th>
              </tr>
            </thead>
            <tbody>
              {loaded.map((item) => (
                <tr key={item.id}>
                  <td className="plan-table-num">{item.loadingSequence}</td>
                  <td>
                    <strong>{item.productCode}</strong>
                    <span className="plan-table-sub">{item.productName}</span>
                  </td>
                  <td className="plan-table-mono">
                    {item.xCm}, {item.yCm}, {item.zCm} cm
                  </td>
                  <td className="plan-table-mono">
                    {item.widthCm}×{item.heightCm}×{item.lengthCm} cm
                  </td>
                  <td>{item.rotationCode ? ROTATION_LABELS[item.rotationCode] : "—"}</td>
                  <td className="plan-table-num">{item.deliverySequence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {rejected.length > 0 ? (
        <section className="plan-table-block">
          <h3>Volumes que ficaram de fora</h3>
          <p className="entity-form-help">
            Estes volumes não entraram no caminhão. O motivo indica o que precisa mudar.
          </p>
          <div className="plan-table-scroll">
            <table className="plan-table">
              <thead>
                <tr>
                  <th scope="col">Produto</th>
                  <th scope="col">Medidas originais</th>
                  <th scope="col">Peso</th>
                  <th scope="col">Motivo</th>
                </tr>
              </thead>
              <tbody>
                {rejected.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.productCode}</strong>
                      <span className="plan-table-sub">{item.productName}</span>
                    </td>
                    <td className="plan-table-mono">
                      {item.originalWidthCm}×{item.originalHeightCm}×{item.originalLengthCm} cm
                    </td>
                    <td className="plan-table-mono">{item.weightKg} kg</td>
                    <td className="plan-table-reason">
                      {item.rejectionReason ? REJECTION_LABELS[item.rejectionReason] : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </>
  );
}
