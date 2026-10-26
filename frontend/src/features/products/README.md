# Feature: products

Listagem e cadastro de produtos (OC26 → **OC27**). Consome `GET/POST/PATCH /products`.

## O que existe hoje

- `pages/ProductListPage.tsx` (+ `.css`): tabela responsiva **paginada**, busca por código/nome e filtro por
  restrição, ambos no servidor antes da paginação (OC95), estados de carregando/vazio/erro e o modal.
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

`CONFIRMADO` (OC105): produto possui `active`; arquivamento é independente das restrições físicas.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem. Só `LOGISTICS_MANAGER` cria e edita — a UI esconde
"Novo produto" e "Editar" para os demais, mas quem barra de verdade é o backend.

## Fora de escopo

Exclusão física não existe no contrato. Busca e restrição são server-side na OC95.

## OC105 — ciclo de vida

`CONFIRMADO`: a tela inicia em somente ativos, permite consultar arquivados ou
ambos pelo filtro `archive_status` no servidor, reiniciando na página 1. A busca
textual e as restrições aprovadas passaram ao servidor na OC95. Cards mostram Ativo/Arquivado.
LOGISTICS_MANAGER vê ações Arquivar/Reativar, que usam o PATCH existente, exibem
loading/erro e atualizam a listagem somente após sucesso. Os demais perfis
preservam as permissões de leitura e não recebem botões de gestão.

## OC95 — pesquisa na coleção

`CONFIRMADO`: a tela envia `search` por code e name.
`restriction=restricted|free` combina com archive_status. Restricted: fragile OR NOT stackable OR NOT rotation_allowed; free: NOT fragile AND stackable AND rotation_allowed.
Mudança de busca/filtro volta à página 1; navegação/refetch preservam critérios.
A API usa SearchListParams e tipos específicos somente onde necessário; o
loader estável não refiltra items localmente. O total vem do conjunto filtrado.
Busca limitada a 120 caracteres; vazio/erro/loading permanecem tratados.
Nenhum campo pessoal proibido pela ADR-017 foi incluído no resumo ou na busca.
