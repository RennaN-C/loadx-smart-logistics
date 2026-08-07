# Feature: products

Listagem e cadastro de produtos (OC26 → **OC27**). Consome `GET/POST/PATCH /products`.

## O que existe hoje

- `pages/ProductListPage.tsx` (+ `.css`): grid **paginado** de cards, busca por código/nome e filtro por
  restrição, ambos client-side **atuando só na página carregada**, estados de carregando/vazio/erro e o modal.
- `components/ProductCard.tsx`: código, nome, descrição, medidas, volume unitário e os chips de restrição.
- `components/ProductForm.tsx`: criação e edição, com volume unitário calculado ao vivo.
- `components/productsErrorMessages.ts`: tradução dos códigos de erro do backend.
- `api/productsApi.ts`: mapeamento snake_case ↔ camelCase.

A listagem usa `hooks/useResourceList` (compartilhado, paginado), não um hook próprio.

## Decisões

**Só as restrições viram chip.** O produto tem três flags (`fragile`, `stackable`, `rotation_allowed`),
mas o caso comum é não ter restrição nenhuma — três selos verdes em todo card seriam ruído. O card mostra
apenas o que limita o encaixe ("Frágil", "Não empilhável", "Sem rotação") e, quando não há nada, um único
chip "Sem restrições". São essas flags que explicam por que um volume foi rejeitado no plano de carga.

**`weight_kg` é `Decimal(10,3)` no backend e chega no JSON como número**, sem união com `string` nem
coerção no adapter, conforme D06 e ADR-016. Antes chegava como string; se voltar a chegar, é regressão
do backend, não do frontend.

**Produto não tem `active`.** Não existe conceito de produto inativo no backend, então não há pill de
status nem filtro por situação — o filtro é por restrição, que é o que muda o planejamento.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem. Só `LOGISTICS_MANAGER` cria e edita — a UI esconde
"Novo produto" e "Editar" para os demais, mas quem barra de verdade é o backend.

## Fora de escopo

Busca e filtro server-side: D12 mantém isso fora do contrato, então o que a tela filtra é apenas a
página carregada — a tela avisa isso em texto. Exclusão não existe rota.
