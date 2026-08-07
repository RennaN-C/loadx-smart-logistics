# Hooks compartilhados

Hooks usados por mais de uma feature. Hook de uma feature só permanece dentro dela
(`features/auth/hooks/useAuth.ts`, por exemplo).

## O que existe hoje

- `useResourceList.ts`: carrega uma **página** da coleção e expõe `status` / `items` / `error` /
  `page` / `total` / `totalPages` / `goToPage` / `refetch`, seguindo o envelope da ADR-017. Nasceu como
  `useTrucks` na OC26, virou genérico na OC28 e ganhou paginação ao integrar a OC59 do backend.

  A função passada precisa ser uma **referência estável** — passar a função exportada do módulo de
  API (`listTrucks`, `listCustomers`, …) já resolve. Uma arrow inline recriada a cada render faria o
  `useEffect` disparar em laço.

  Busca e filtro continuam no cliente e valem só para a página carregada: D12 mantém filtro
  server-side fora do contrato. Quem usa o hook deve dizer isso na tela (`.entity-summary`), senão o
  usuário acha que buscou na base inteira e conclui que o registro não existe.

- `useEditTarget.ts`: busca o registro **completo** por id antes de abrir o formulário de edição.
  As listagens de clientes, motoristas e pedidos devolvem um resumo — dado pessoal e itens só saem no
  detalhe —, então editar a partir do que veio na lista mandaria um PATCH com campos faltando.
