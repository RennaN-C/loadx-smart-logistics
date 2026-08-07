# Feature: products

Listagem e cadastro de produtos (OC26 → **OC27**). Consome `GET/POST/PATCH /products`.

## O que existe hoje

- `pages/ProductListPage.tsx` (+ `.css`): grid de cards, busca por código/nome e filtro por restrição,
  ambos **client-side** (o backend não aceita query param), estados de carregando/vazio/erro e o modal.
- `components/ProductCard.tsx`: código, nome, descrição, medidas, volume unitário e os chips de restrição.
- `components/ProductForm.tsx`: criação e edição, com volume unitário calculado ao vivo.
- `components/productsErrorMessages.ts`: tradução dos códigos de erro do backend.
- `api/productsApi.ts`: mapeamento snake_case ↔ camelCase.
- `hooks/useProducts.ts`: carga da lista + `refetch`.

## Decisões

**Só as restrições viram chip.** O produto tem três flags (`fragile`, `stackable`, `rotation_allowed`),
mas o caso comum é não ter restrição nenhuma — três selos verdes em todo card seriam ruído. O card mostra
apenas o que limita o encaixe ("Frágil", "Não empilhável", "Sem rotação") e, quando não há nada, um único
chip "Sem restrições". São essas flags que explicam por que um volume foi rejeitado no plano de carga.

**`weight_kg` é `Decimal(10,3)` no backend** e, como todo `Decimal` deste projeto, chega no JSON como
**string**. O mapeamento converte com `Number(...)`, e há teste cobrindo os dois formatos.

**Produto não tem `active`.** Não existe conceito de produto inativo no backend, então não há pill de
status nem filtro por situação — o filtro é por restrição, que é o que muda o planejamento.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem. Só `LOGISTICS_MANAGER` cria e edita — a UI esconde
"Novo produto" e "Editar" para os demais, mas quem barra de verdade é o backend.

## Fora de escopo

Paginação e busca server-side (não suportadas pelo backend) e exclusão (não existe rota).
