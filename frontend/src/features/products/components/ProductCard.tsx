import { StatusPill } from "../../../components/StatusPill";
import type { Product } from "../types";

const weightFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });
const volumeFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

/**
 * Só as restrições aparecem como chip. Um produto sem restrição nenhuma é o caso
 * comum e não precisa de três selos verdes; o que interessa a quem planeja carga
 * é o que limita o encaixe.
 */
function restrictionsOf(product: Product): string[] {
  const restrictions: string[] = [];
  if (product.fragile) restrictions.push("Frágil");
  if (!product.stackable) restrictions.push("Não empilhável");
  if (!product.rotationAllowed) restrictions.push("Sem rotação");
  return restrictions;
}

interface ProductCardProps {
  readonly product: Product;
  readonly canManage: boolean;
  readonly onEdit: (product: Product) => void;
}

export function ProductCard({ product, canManage, onEdit }: ProductCardProps) {
  const volumeM3 = (product.widthCm / 100) * (product.heightCm / 100) * (product.lengthCm / 100);
  const restrictions = restrictionsOf(product);

  return (
    <article className="product-card">
      <div className="product-card-head">
        <div>
          <p className="product-card-code">{product.code}</p>
          <p className="product-card-name">{product.name}</p>
        </div>
        <span className="product-card-weight">{weightFormatter.format(product.weightKg)} kg</span>
      </div>

      {product.description ? <p className="product-card-description">{product.description}</p> : null}

      <dl className="product-card-specs">
        <div>
          <dt>LARGURA</dt>
          <dd>{product.widthCm} cm</dd>
        </div>
        <div>
          <dt>ALTURA</dt>
          <dd>{product.heightCm} cm</dd>
        </div>
        <div>
          <dt>COMPR.</dt>
          <dd>{product.lengthCm} cm</dd>
        </div>
        <div>
          <dt>VOLUME</dt>
          <dd>{volumeFormatter.format(volumeM3)} m³</dd>
        </div>
      </dl>

      <div className="product-card-foot">
        <div className="product-card-flags">
          {restrictions.length > 0 ? (
            restrictions.map((restriction) => (
              <StatusPill key={restriction} tone="warn">
                {restriction}
              </StatusPill>
            ))
          ) : (
            <StatusPill tone="good">Sem restrições</StatusPill>
          )}
        </div>
        {canManage ? (
          <button type="button" className="btn-link" onClick={() => onEdit(product)}>
            Editar
          </button>
        ) : null}
      </div>
    </article>
  );
}
