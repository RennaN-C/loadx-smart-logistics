import { RecordLifecycleAction } from "../../../components/RecordLifecycleAction";
import { StatusPill } from "../../../components/StatusPill";
import { RowActions } from "../../../components/RowActions";
import type { Product } from "../types";

const weightFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

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
  readonly onChanged: () => Promise<void>;
  readonly onEdit: (product: Product) => void;
}

export function ProductCard({ product, canManage, onEdit, onChanged }: ProductCardProps) {
  const restrictions = restrictionsOf(product);

  return (
    <tr className="product-card">
      <td data-label="Código"><strong className="product-card-code">{product.code}</strong></td>
      <td data-label="Produto"><strong className="product-card-name">{product.name}</strong>{product.description ? <small>{product.description}</small> : null}</td>
      <td data-label="Dimensões">{product.widthCm} × {product.heightCm} × {product.lengthCm} cm</td>
      <td data-label="Peso"><strong className="product-card-weight">{weightFormatter.format(product.weightKg)} kg</strong></td>
      <td data-label="Restrições"><div className="product-card-flags">
          {restrictions.length > 0 ? (
            restrictions.map((restriction) => (
              <StatusPill key={restriction} tone="warn">
                {restriction}
              </StatusPill>
            ))
          ) : (
            <StatusPill tone="good">Sem restrições</StatusPill>
          )}
        </div></td>
      <td data-label="Situação"><StatusPill tone={product.active ? "good" : "neutral"}>{product.active ? "Ativo" : "Arquivado"}</StatusPill></td>
      <td data-label="Ações">{canManage ? <RowActions label={`Ações do produto ${product.code}`}><button type="button" className="btn-link" onClick={() => onEdit(product)}>Editar</button><RecordLifecycleAction resource="products" id={product.id} active={product.active} onChanged={onChanged} /></RowActions> : <span className="registry-no-action">Somente consulta</span>}</td>
    </tr>
  );
}
