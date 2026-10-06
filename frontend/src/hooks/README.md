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

- `useFieldErrors.ts`: guarda os erros POR CAMPO de um formulário — os que a tela detecta antes de
  enviar e os que o backend devolve em 422 — e devolve `errors` / `formRef` / `validateAll` /
  `revalidate` / `applyApiError` / `clearAll`. Nasceu na OC71, quando clientes e motoristas passaram
  a precisar da mesma mecânica: dois formulários com a lógica copiada seriam duplicação pura.

  As chaves são os `id` dos controles (`customer-document`), não os nomes da API. É isso que deixa
  `fieldErrorProps(id, errors[id])` ser direto e o `aria-describedby` apontar para o parágrafo certo;
  `applyApiError` recebe o mapa `campo da API → id do controle` para fazer a tradução.

  A validação só começa no primeiro envio — validar antes acusa "CPF inválido" no terceiro dígito,
  com a pessoa ainda digitando. Depois do envio, `revalidate` corrige o campo a cada tecla.

  O foco vai para o primeiro campo inválido, e por isso existe o contador `focusRequest`: dois envios
  seguidos com o mesmo erro precisam mandar o foco de volta, e um booleano que já é `true` não
  dispararia o efeito. O foco é movido no efeito, depois do render — antes dele o `aria-invalid`
  ainda não está no DOM.
