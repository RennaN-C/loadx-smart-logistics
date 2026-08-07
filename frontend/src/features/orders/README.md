# Feature: orders

Listagem e cadastro de pedidos (OC29). Consome `GET/POST/PATCH /orders`.

## O que existe hoje

- `pages/OrderListPage.tsx` (+ `.css`): grid de cards, busca por cliente/endereço e filtro por
  situação, ambos client-side, estados de carregando/vazio/erro e o modal.
- `components/OrderCard.tsx`: cliente, endereço, situação, prioridade, previsão e os itens em ordem
  de entrega.
- `components/OrderForm.tsx`: formulário mestre-detalhe — o primeiro do projeto com lista de itens.
- `components/orderDateTime.ts`: ponte entre o `<input type="datetime-local">` e o contrato da API.
- `components/orderLabels.ts`: rótulos em português para situação e prioridade.
- `components/ordersErrorMessages.ts`: tradução dos códigos de erro.
- `api/ordersApi.ts`: mapeamento snake_case ↔ camelCase, incluindo os itens aninhados.

## Três coisas que não existiam nas telas anteriores

**Formulário com lista de itens.** O backend exige no mínimo um item, então o formulário nasce com um
e o botão "Remover" fica desabilitado enquanto só houver esse. Cada linha tem chave própria (contador
em `useRef`), não índice do array — com índice, remover o primeiro item faria o React reaproveitar o
estado do errado.

**`expected_delivery_at` exige fuso.** O validador do backend (`normalize_optional_utc`) recusa
datetime ingênuo, mas o `<input type="datetime-local">` devolve exatamente isso (`2026-08-10T14:30`,
hora local). `orderDateTime.ts` converte nos dois sentidos e é testado por ida e volta, para o teste
não depender do fuso da máquina que roda a suíte.

**Ids crus.** O pedido devolve só `customer_id` e `product_id`, e não há endpoint de busca. A página
carrega as listas completas de clientes e produtos e resolve os nomes em memória. Quando o id não está
mais na lista, o card mostra "Cliente não encontrado" / "Produto não encontrado" em vez de um espaço
vazio.

## Prioridade: convenção, não contrato

`priority` aceita **qualquer string de até 32 caracteres** no backend — não há enum, ao contrário de
`status`. O frontend oferece `LOW`, `NORMAL`, `HIGH` e `URGENT` num `<select>` para não virar campo
livre, mas isso é convenção adotada aqui, não contrato acordado. Registrado como
`DECISÃO NECESSÁRIA` em `docs/11-riscos-pendencias.md`. `priorityLabel()` cai no valor cru quando
recebe algo fora da lista, para não esconder dado vindo de outra origem.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem. Só `LOGISTICS_MANAGER` cria e edita.

## Fora de escopo

Paginação e busca server-side (não suportadas pelo backend) e exclusão (não existe rota). Alterar
itens de pedido já usado em plano de carga é recusado pelo backend com
`ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN`, e a mensagem explica isso.
