# Feature: orders

Listagem e cadastro de pedidos (OC29). Consome `GET/POST/PATCH /orders`.

## O que existe hoje

- `pages/OrderListPage.tsx` (+ `.css`): tabela responsiva **paginada**, busca por cliente e filtro por
  situação, ambos no servidor antes da paginação (OC95), estados de carregando/vazio/erro e o modal.
- `components/OrderCard.tsx`: linha com referência navegável, cliente, situação,
  prioridade, previsão e a **contagem** de itens; ações secundárias sob demanda.
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
isso pode aparecer com frequência. OC95 preserva esse fallback e não amplia
`OrderListRead`: para ADMIN/LOGISTICS_MANAGER, a busca por nome acontece no
backend, independentemente deste mapa de apresentação. CHECKER busca somente
referências UUID, sem consultar nomes de clientes.

## Prioridade: contrato oficial

`CONFIRMADO`: `priority` aceita somente `LOW`, `NORMAL`, `HIGH` e `URGENT`. A entrada é normalizada
para maiúsculas antes da validação, e o `<select>` do frontend oferece os mesmos quatro valores.
`priorityLabel()` mantém o fallback para o valor cru recebido, sem esconder eventual dado legado.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem. `ADMIN` e `LOGISTICS_MANAGER` criam e editam. `CHECKER` não consulta cadastros de clientes; nessa leitura a referência do cliente permanece visível sem solicitar uma API proibida.

## Fora de escopo

`CONFIRMADO`: a paginação é suportada pelo backend e consumida pela tela.
Exclusão permanece fora do contrato. Alterar
itens de pedido já usado em plano de carga é recusado pelo backend com
`ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN`, e a mensagem explica isso.

## Navegação persistente (auditoria #188)

`CONFIRMADO`: os cards abrem leitura do pedido em `/orders?order=<id>`, usando
`GET /orders/{id}`. A URL permite F5, acesso direto e histórico do navegador;
fechar o detalhe preserva os demais parâmetros da listagem. O detalhe é somente
leitura, inclui o endereço persistido e os itens, e respeita os perfis existentes.
A edição continua sendo uma ação separada. Nenhum dado é salvo em localStorage.

## OC95 — pesquisa na coleção

`CONFIRMADO`: ADMIN e LOGISTICS_MANAGER usam `search` por nome do cliente,
UUID do pedido e UUID do cliente. CHECKER vê "Buscar por referência", não
carrega clientes e pesquisa somente UUID do pedido e UUID do cliente. O backend
também impõe essa fronteira: um termo que só corresponde ao nome retorna 200
com coleção filtrada vazia para CHECKER, inclusive em chamada direta à API.
DRIVER continua 403; schemas resumidos e RBAC dos endpoints são preservados.
`status` aceita apenas o catálogo público ORDER_STATUS_VALUES; combina por AND com search.
Mudança de busca/filtro volta à página 1; navegação/refetch preservam critérios.
A API usa SearchListParams e tipos específicos somente onde necessário; o
loader estável não refiltra items localmente. O total vem do conjunto filtrado.
Busca limitada a 120 caracteres; vazio/erro/loading permanecem tratados.
Nenhum campo pessoal proibido pela ADR-017 foi incluído no resumo ou na busca.

## Revisão visual de 24/10/2026

`CONFIRMADO`: o seletor de situação é o ponto único para filtrar todos os
estados, incluindo Entregue. Foram removidos os botões redundantes Todos os
pedidos/Pedidos entregues; URLs com `status=DELIVERED` continuam compatíveis.
Ver pedido, Anexos e Editar preservam os handlers existentes no menu da linha.
O UUID abreviado abre o detalhe persistido.
