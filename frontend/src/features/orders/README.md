# Feature: orders

Listagem e cadastro de pedidos (OC29). Consome `GET/POST/PATCH /orders`.

## O que existe hoje

- `pages/OrderListPage.tsx` (+ `.css`): grid **paginado** de cards, busca por cliente e filtro por
  situação, ambos client-side **na página carregada**, estados de carregando/vazio/erro e o modal.
- `components/OrderCard.tsx`: cliente, situação, prioridade, previsão e a **contagem** de itens.
- `components/OrderForm.tsx`: formulário mestre-detalhe — o primeiro do projeto com lista de itens.
- `components/orderDateTime.ts`: ponte entre o `<input type="datetime-local">` e o contrato da API.
- `components/orderLabels.ts`: rótulos em português para situação e prioridade.
- `components/ordersErrorMessages.ts`: tradução dos códigos de erro.
- `api/ordersApi.ts`: mapeamento snake_case ↔ camelCase, incluindo os itens aninhados, e
  `changeOrderStatus` para o endpoint dedicado de situação.

## Situação tem endpoint próprio (OC52)

`PATCH /orders/{id}` usa `extra="forbid"` e **recusa `status` com 422** — a troca de situação vai por
`PATCH /orders/{id}/status`. O formulário chama os dois: primeiro os campos, depois a situação, e só
quando ela mudou.

As transições manuais permitidas pelo backend (`MANUAL_ORDER_STATUS_TRANSITIONS`) são apenas:

| de | para |
|---|---|
| `DRAFT` | `READY`, `CANCELED` |
| `READY` | `DRAFT`, `CANCELED` |

A partir de `PLANNED`, `IN_TRANSIT`, `DELIVERED` ou `CANCELED` não há saída manual: quem move dali é o
planejamento, a viagem ou a entrega. Nesses casos o campo vira somente leitura, em vez de oferecer uma
opção que voltaria 409 `ORDER_STATUS_TRANSITION_NOT_ALLOWED`.

## Três coisas que não existiam nas telas anteriores

**Formulário com lista de itens.** O backend exige no mínimo um item, então o formulário nasce com um
e o botão "Remover" fica desabilitado enquanto só houver esse. Cada linha tem chave própria (contador
em `useRef`), não índice do array — com índice, remover o primeiro item faria o React reaproveitar o
estado do errado.

**`expected_delivery_at` exige fuso.** O validador do backend (`normalize_optional_utc`) recusa
datetime ingênuo, mas o `<input type="datetime-local">` devolve exatamente isso (`2026-08-10T14:30`,
hora local). `orderDateTime.ts` converte nos dois sentidos e é testado por ida e volta, para o teste
não depender do fuso da máquina que roda a suíte.

**A listagem devolve um resumo.** `GET /orders` responde `OrderListRead`: sem `delivery_address` e sem
`items` — só `item_count`. O card mostra a contagem, e editar exige `GET /orders/{id}` antes de abrir o
formulário (`hooks/useEditTarget`), senão o PATCH iria sem os itens.

**Ids crus.** O pedido traz só `customer_id`. A página carrega a listagem de clientes para resolver o
nome, mas essa listagem também é paginada: um cliente fora da página carregada não resolve, e o card
mostra "Cliente não encontrado" em vez de um espaço vazio. `RISCO IDENTIFICADO`: com muitos clientes
isso vai aparecer com frequência, e o caminho certo é o backend devolver o nome no `OrderListRead` ou
abrir busca por id.

## Prioridade: contrato oficial

`CONFIRMADO`: `priority` aceita somente `LOW`, `NORMAL`, `HIGH` e `URGENT`. A entrada é normalizada
para maiúsculas antes da validação, e o `<select>` do frontend oferece os mesmos quatro valores.
`priorityLabel()` mantém o fallback para o valor cru recebido, sem esconder eventual dado legado.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem. Só `LOGISTICS_MANAGER` cria e edita.

## Fora de escopo

Paginação e busca server-side (não suportadas pelo backend) e exclusão (não existe rota). Alterar
itens de pedido já usado em plano de carga é recusado pelo backend com
`ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN`, e a mensagem explica isso.
