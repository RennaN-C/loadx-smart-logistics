# ADR-009: colisão AABB sem tolerância

Status: aceita

## Contexto

O posicionamento first-fit da OC15 delega as regras físicas a uma política obrigatória. A OC16 precisa transformar a classificação geométrica entre caixas AABB em uma decisão de colisão determinística, sem antecipar apoio, empilhamento, fragilidade ou a engine completa.

## Decisão

- Duas caixas AABB colidem somente quando a interseção possui extensão estritamente positiva nos três eixos `x`, `y` e `z`, relação classificada como `POSITIVE_OVERLAP`.
- Contato por face, aresta ou vértice possui extensão zero em pelo menos um eixo e não é colisão.
- As comparações usam coordenadas e dimensões inteiras em centímetros, por igualdade exata e com tolerância geométrica zero.
- `is_collision_free(candidate_box, placed_boxes)` aceita o candidato somente quando nenhuma caixa já posicionada possui `POSITIVE_OVERLAP` com ele.
- A decisão de colisão não depende da ordem das caixas já posicionadas.
- A OC16 não decide limites, apoio, empilhamento, fragilidade, peso ou sequência de carregamento.
- A OC16 não cria um motivo público `COLLISION`; o catálogo de rejeições e sua precedência permanecem como gate da engine.

## Consequências

- Caixas podem compartilhar face, aresta ou vértice sem invalidar o candidato por colisão.
- Qualquer sobreposição positiva, inclusive de um centímetro, invalida o candidato.
- O validador de colisão permanece uma regra pura e isolada; ele não torna uma posição publicável sem as validações posteriores e a revalidação física integrada.
- Alterar a semântica de contato ou introduzir tolerância exigirá nova `algorithm_version` quando a engine estiver integrada.
