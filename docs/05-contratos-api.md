# Contratos iniciais da API

Este documento é o contrato combinado entre backend, frontend, algoritmo e integrações. Alterações devem ser discutidas, versionadas e refletidas em testes.

## Convenções

- `CONFIRMADO`: prefixo oficial da API de negócio: `/api/v1`.
- `CONFIRMADO`: os endpoints operacionais `/health` e `/ready` ficam fora do
  prefixo de negócio.
- `CONFIRMADO`: JSON usa campos em snake_case.
- `CONFIRMADO` por D06 e `ADR-016`: campos decimais públicos usam número JSON
  na entrada e na saída. Strings numéricas e booleanos são inválidos. O backend
  preserva `Decimal` internamente e cada campo mantém a precisão e escala do
  modelo aprovado; zeros finais não fazem parte do valor JSON.
- `RECOMENDAÇÃO`: caminhos usam kebab-case quando tiverem mais de uma palavra, como `/load-plans`.
- `CONFIRMADO` por D12 e `ADR-017`: coleções usam `page` 1-based (default `1`),
  `page_size` (default `20`, mínimo `1`, máximo `100`) e `sort_order`
  (`asc` ou `desc`, default `desc`). A ordenação é por `created_at`, com `id`
  como desempate na mesma direção.
- `CONFIRMADO`: coleções retornam `items`, `page`, `page_size`, `total` e
  `total_pages`. Página além do fim retorna `items` vazio; coleção vazia retorna
  `total_pages = 0`.
- `CONFIRMADO`: não há `sort_by`, busca livre ou filtros por dados pessoais na
  OC59. Todo filtro futuro usa query param em snake_case e whitelist documentada.
- `CONFIRMADO`: em atualizações parciais, campos omitidos permanecem inalterados; `null` só é aceito para campos anuláveis no modelo de dados.

## Autenticação

Endpoint público de negócio:

- `POST /auth/login`.

Endpoints públicos operacionais:

- `GET /health`.
- `GET /ready`.

Endpoint disponível para qualquer usuário autenticado:

- `GET /auth/me`.
- `POST /auth/logout`.

Exemplo de login:

```json
{
  "email": "admin@example.test",
  "password": "senha-local"
}
```

Resposta `200`: o mesmo contrato `UserRead` usado por `/auth/me`.

```json
{
  "id": "uuid",
  "name": "Admin Local",
  "email": "admin@example.test",
  "role": "ADMIN",
  "driver_id": null,
  "active": true,
  "created_at": "2026-08-08T12:00:00Z"
}
```

O login envia o identificador somente em cookie. Em produção:

```text
Set-Cookie: __Host-loadx_session=<opaque>; Path=/; Secure; HttpOnly; SameSite=Lax
```

`CONFIRMADO` por D18 e `ADR-020`: o cookie não usa `Domain`, contém pelo menos
256 bits aleatórios e somente seu hash é persistido. No ambiente local HTTP, o
nome é `loadx_session` e `Secure` fica desabilitado; o prefixo `__Host-` nunca é
emitido com atributos incompatíveis.

`POST /auth/login` e `GET /auth/me` retornam também `X-CSRF-Token` no header. O
frontend mantém esse valor somente em memória e o envia em todo `POST`, `PUT`,
`PATCH` ou `DELETE` autenticado:

```text
X-CSRF-Token: <session-bound-token>
```

`POST /auth/logout` exige cookie, `Origin` e `X-CSRF-Token`, retorna `204`, revoga
a sessão atual e expira o cookie.

Erros específicos:

- `AUTH_INVALID_CREDENTIALS`: e-mail ou senha inválidos.
- `AUTH_INVALID_TOKEN`: sessão ausente, inválida, revogada, expirada ou usuário
  inexistente.
- `AUTH_USER_INACTIVE`: usuário inativo.
- `AUTH_FORBIDDEN`: usuário autenticado sem permissão para a ação.
- `AUTH_RATE_LIMITED`: login temporariamente limitado; usa `429` e
  `Retry-After` inteiro em segundos.
- `AUTH_ORIGIN_FORBIDDEN`: método inseguro sem origem aprovada.
- `AUTH_CSRF_INVALID`: token CSRF ausente ou inválido.

`CONFIRMADO`: `POST /auth/register` foi removido do contrato por `D03` e `ADR-004`. O primeiro `ADMIN` é criado por comando administrativo local; os usuários seguintes são criados por `ADMIN` em `POST /users`.

`CONFIRMADO`: depois das migrations e antes de expor a API, o bootstrap é executado em `backend` com `python -m app.modules.auth.bootstrap` ou, pela raiz, com `docker compose run --rm backend python -m app.modules.auth.bootstrap`. A senha é lida de forma oculta e o comando recusa execução quando já existe qualquer usuário.

`CONFIRMADO`: ausência ou invalidade de autenticação retorna `401
AUTH_INVALID_TOKEN`; autenticação válida sem permissão retorna `403
AUTH_FORBIDDEN`.

`CONFIRMADO`: após a `OC51-G`, todos os endpoints de negócio atualmente implementados exigem autenticação e aplicam a matriz aprovada.

`CONFIRMADO` por D18 e `ADR-020`: não existe refresh token. A sessão expira após
30 minutos de inatividade ou 8 horas absolutas. Login é limitado por conta e IP
com atrasos de 1, 5, 15 e 60 minutos a partir da quinta falha. Conta inexistente,
senha inválida e usuário inativo retornam `401 AUTH_INVALID_CREDENTIALS` sem
revelar qual condição ocorreu.

## Saúde

### GET `/health`

```json
{
  "status": "ok",
  "service": "loadx-api"
}
```

`CONFIRMADO`: `/health` é liveness e não consulta PostgreSQL ou Alembic.

### GET `/ready`

Resposta `200` quando PostgreSQL está acessível e `alembic_version` corresponde
exatamente aos heads entregues com a aplicação:

```json
{
  "status": "ready",
  "service": "loadx-api"
}
```

Resposta `503` para banco indisponível, timeout, tabela de versão ausente ou
revisão divergente:

```json
{
  "code": "SERVICE_NOT_READY",
  "message": "O serviço não está pronto.",
  "details": []
}
```

`CONFIRMADO` por D11 e `ADR-018`: a verificação é somente leitura, não aplica
migrations, possui orçamento total de 2 segundos e não expõe componente, URL,
credencial, revisão, exceção ou stack trace.

## Usuários

- `GET /users`.
- `POST /users`.
- `GET /users/{id}`.
- `PATCH /users/{id}`.

Regras do contrato aprovado:

- Todas as rotas de `/users` exigem perfil `ADMIN`.
- A listagem retorna somente `id`, `name`, `role`, `active` e `created_at`.
- Detalhe e respostas de escrita retornam `id`, `name`, `email`, `role`,
  `driver_id`, `active` e `created_at`.
- `password_hash` nunca é retornado.
- `role` aceita `ADMIN`, `CHECKER`, `DRIVER` e `LOGISTICS_MANAGER`.
- `email` é normalizado para minúsculas.
- `role` é normalizado para maiúsculas.
- `driver_id` é opcional; valor não nulo exige `role = DRIVER`, motorista
  existente e vínculo não utilizado por outro usuário.
- Alterar `driver_id` revoga todas as sessões do usuário na mesma transação.
- `password` deve ter entre 15 e 128 caracteres na entrada, aceita espaços e
  Unicode e não exige composição artificial.

Erros específicos:

- `USER_NOT_FOUND`: usuário não encontrado.
- `USER_EMAIL_ALREADY_EXISTS`: e-mail já cadastrado.
- `USER_LAST_ACTIVE_ADMIN_REQUIRED`: alteração deixaria o sistema sem `ADMIN` ativo.
- `USER_DRIVER_NOT_FOUND`: `driver_id` não referencia motorista existente.
- `USER_DRIVER_ALREADY_LINKED`: motorista já está vinculado a outro usuário.
- `USER_DRIVER_ROLE_REQUIRED`: vínculo foi informado para papel diferente de
  `DRIVER`.

`CONFIRMADO`: não existe cadastro público. O primeiro `ADMIN` usa bootstrap local e, depois, usuários são criados somente por `ADMIN`.

## Caminhões

- `GET /trucks`.
- `POST /trucks`.
- `GET /trucks/{id}`.
- `PATCH /trucks/{id}`.

Regras de autorização:

- `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem usar `GET`.
- Somente `LOGISTICS_MANAGER` pode usar `POST` e `PATCH`.
- `DRIVER` não acessa essas rotas na API atual.

Exemplo de criação:

```json
{
  "plate": "ABC1D23",
  "model": "Bau medio",
  "internal_width_cm": 240,
  "internal_height_cm": 260,
  "internal_length_cm": 600,
  "max_weight_kg": 8000
}
```

`RECOMENDAÇÃO`: exclusão deve ser lógica por `active = false` até a equipe aprovar regra de delete físico.

## Produtos

- `GET /products`.
- `POST /products`.
- `GET /products/{id}`.
- `PATCH /products/{id}`.

Regras de autorização:

- `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem usar `GET`.
- Somente `LOGISTICS_MANAGER` pode usar `POST` e `PATCH`.
- `DRIVER` não acessa essas rotas na API atual.

Exemplo de criação:

```json
{
  "code": "CX-A",
  "name": "Caixa A",
  "description": "Produto de demonstracao",
  "width_cm": 60,
  "height_cm": 50,
  "length_cm": 40,
  "weight_kg": 12.5,
  "fragile": false,
  "stackable": true,
  "rotation_allowed": true
}
```

## Clientes

- `GET /customers`.
- `POST /customers`.
- `GET /customers/{id}`.
- `PATCH /customers/{id}`.

Regras de autorização:

- `ADMIN` e `LOGISTICS_MANAGER` podem usar `GET`.
- Somente `LOGISTICS_MANAGER` pode usar `POST` e `PATCH`.
- `CHECKER` e `DRIVER` não acessam essas rotas.

Campos de `GET /customers`: `id`, `name`, `city`, `state` e `created_at`.
Documento, telefone, endereço e observações aparecem somente no detalhe e nas
respostas de escrita já protegidas pelo RBAC.

## Motoristas

- `GET /drivers`.
- `POST /drivers`.
- `GET /drivers/{id}`.
- `PATCH /drivers/{id}`.

Regras de autorização:

- `ADMIN` e `LOGISTICS_MANAGER` podem usar `GET`.
- Somente `LOGISTICS_MANAGER` pode usar `POST` e `PATCH`.
- `CHECKER` e `DRIVER` não acessam essas rotas.

Campos de `GET /drivers`: `id`, `name`, `license_category`, `active` e
`created_at`. Documento, telefone e número da CNH aparecem somente no detalhe e
nas respostas de escrita já protegidas pelo RBAC.

## Pedidos

- `GET /orders`.
- `POST /orders`.
- `GET /orders/{id}`.
- `PATCH /orders/{id}`.
- `PATCH /orders/{id}/status`.

Regras de autorização:

- `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem usar `GET`.
- Somente `LOGISTICS_MANAGER` pode usar `POST` e `PATCH`.
- `DRIVER` não acessa essas rotas na API atual; sua operação ocorre pelos
  endpoints da viagem atribuída.

Exemplo de criação:

```json
{
  "customer_id": "uuid",
  "priority": "NORMAL",
  "delivery_address": "Rua Exemplo, 100",
  "expected_delivery_at": "2026-08-10T13:00:00Z",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 3,
      "delivery_sequence": 1
    }
  ]
}
```

Regras atuais:

- `GET /orders` retorna `id`, `customer_id`, `status`, `priority`,
  `expected_delivery_at`, `created_at` e `item_count`; omite
  `delivery_address` e os itens completos.

- `POST /orders` cria o pedido com `status = "DRAFT"`.
- `PATCH /orders/{id}` aceita alteração de `customer_id`, `priority`,
  `delivery_address`, `expected_delivery_at` e, quando `items` for enviado,
  substitui o conjunto somente em `DRAFT` e se nenhum item estiver referenciado
  por plano. O payload rejeita `status` e campos desconhecidos.
- `PATCH /orders/{id}/status` recebe `{"status": "READY"}` e aplica somente a
  matriz de transições manuais de D04. Aprovação de plano, início de viagem e
  conclusão de entrega mantêm seus próprios casos de uso.
- `status` aceita `DRAFT`, `READY`, `PLANNED`, `IN_TRANSIT`, `DELIVERED` e `CANCELED`.
- `priority` aceita `LOW`, `NORMAL`, `HIGH` e `URGENT` e é normalizado para
  maiúsculas. Outro valor na criação ou atualização retorna o erro padronizado
  de validação com status `422`.
- `expected_delivery_at` deve vir com timezone e é normalizado para UTC.
- O pedido deve possuir pelo menos um item.
- `quantity` e `delivery_sequence` devem ser maiores que zero.
- Todos os itens do mesmo pedido devem usar a mesma `delivery_sequence` na
  OC09; pedidos diferentes podem compartilhar o valor e usam UUID como
  desempate determinístico.
- `customer_id` deve existir em `customers`.
- Todos os `product_id` dos itens devem existir em `products`.

Erros específicos:

- `ORDER_NOT_FOUND`: pedido não encontrado.
- `ORDER_CUSTOMER_NOT_FOUND`: cliente do pedido não encontrado.
- `ORDER_PRODUCT_NOT_FOUND`: produto do pedido não encontrado.
- `ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN`: conflito `409`; os itens históricos não
  podem ser substituídos.
- `ORDER_EDIT_NOT_ALLOWED`: conflito `409`; o pedido não está em `DRAFT`.
- `ORDER_STATUS_TRANSITION_NOT_ALLOWED`: conflito `409`; a origem e o destino
  não formam uma transição manual aprovada.

`CONFIRMADO`: criação e cada transição efetiva persistem pedido e histórico em
uma única transação. A criação registra `null -> DRAFT`; repetir o estado atual
retorna o pedido sem criar histórico duplicado.

## Planos de carga

Regras de autorização:

- Somente `LOGISTICS_MANAGER` usa criação, comparação, aprovação e recálculo.
- `ADMIN` e `LOGISTICS_MANAGER` consultam e solicitam explicação de qualquer plano
  persistido tecnicamente válido.
- `CHECKER` consulta e solicita explicação somente de plano `APPROVED`.
- `DRIVER` não acessa os endpoints de plano de carga; a viagem usa internamente o
  plano atribuído.

### POST `/load-plans`

```json
{
  "truck_id": "uuid",
  "order_ids": ["uuid"]
}
```

`order_ids` deve conter ao menos um UUID e não aceita duplicatas. O caminhão deve
estar ativo, todos os pedidos devem estar em `READY` e a soma das quantidades não
pode exceder 200 volumes.

Resposta `201`, também usada por `GET /load-plans/{id}`:

```json
{
  "id": "uuid",
  "truck_id": "uuid",
  "recalculated_from_id": null,
  "status": "CALCULATED",
  "internal_volume_cm3": 37440000,
  "used_volume_cm3": 32400000,
  "occupancy_percent": 86.54,
  "total_weight_kg": 5420.000,
  "loaded_count": 28,
  "unloaded_count": 0,
  "algorithm_version": "heuristic-v1",
  "created_at": "2026-08-04T12:00:00Z",
  "approved_at": null,
  "order_ids": ["uuid"],
  "items": [
    {
      "id": "load-plan-item-uuid",
      "order_id": "uuid",
      "order_item_id": "uuid",
      "product_id": "uuid",
      "volume_index": 1,
      "quantity": 1,
      "delivery_sequence": 2,
      "product_code": "CX-A",
      "product_name": "Caixa A",
      "original_width_cm": 60,
      "original_height_cm": 50,
      "original_length_cm": 40,
      "weight_kg": 12.500,
      "fragile": false,
      "stackable": true,
      "rotation_allowed": true,
      "x_cm": 0,
      "y_cm": 0,
      "z_cm": 0,
      "width_cm": 60,
      "height_cm": 50,
      "length_cm": 40,
      "rotation_code": "XYZ",
      "loading_sequence": 1,
      "placed": true,
      "rejection_reason": null
    }
  ]
}
```

Os campos físicos e descritivos de caminhão/produto/item são snapshots do momento
do cálculo. `Decimal` permanece no domínio, no schema interno e na persistência;
a fronteira HTTP usa número JSON conforme D06 e `ADR-016`.

### GET `/load-plans/{id}/visualization`

```json
{
  "truck": {
    "id": "uuid",
    "plate": "ABC1D23",
    "model": "Bau medio",
    "width_cm": 240,
    "height_cm": 260,
    "length_cm": 600,
    "max_weight_kg": 8000.00
  },
  "items": [
    {
      "id": "load-plan-item-uuid",
      "order_id": "uuid",
      "order_item_id": "uuid",
      "product_id": "uuid",
      "volume_index": 1,
      "quantity": 1,
      "delivery_sequence": 2,
      "product_code": "CX-A",
      "product_name": "Caixa A",
      "original_width_cm": 60,
      "original_height_cm": 50,
      "original_length_cm": 40,
      "weight_kg": 12.500,
      "fragile": false,
      "stackable": true,
      "rotation_allowed": true,
      "x_cm": 0,
      "y_cm": 0,
      "z_cm": 0,
      "width_cm": 60,
      "height_cm": 50,
      "length_cm": 40,
      "rotation_code": "XYZ",
      "loading_sequence": 1
    }
  ],
  "unloaded_items": [
    {
      "id": "load-plan-item-uuid",
      "order_id": "uuid",
      "order_item_id": "uuid",
      "product_id": "uuid",
      "volume_index": 1,
      "quantity": 1,
      "delivery_sequence": 1,
      "product_code": "CX-B",
      "product_name": "Caixa B",
      "original_width_cm": 300,
      "original_height_cm": 300,
      "original_length_cm": 300,
      "weight_kg": 20.000,
      "fragile": false,
      "stackable": true,
      "rotation_allowed": false,
      "rejection_reason": "TRUCK_DIMENSIONS_EXCEEDED"
    }
  ]
}
```

`CONFIRMADO`: `rejection_reason` aceita somente, em ordem de precedência, `TRUCK_DIMENSIONS_EXCEEDED`, `TRUCK_WEIGHT_EXCEEDED`, `NON_STACKABLE_SUPPORT`, `FRAGILE_SUPPORT_WEIGHT_EXCEEDED`, `INSUFFICIENT_SUPPORT`, `COLLISION` ou `NO_VALID_POSITION`. Entrada inválida gera erro de domínio/API e não aparece como volume rejeitado.

`CONFIRMADO`: conforme `ADR-007`, `rotation_code` usa somente `XYZ`, `XZY`, `YXZ`, `YZX`, `ZXY` ou `ZYX`. As letras indicam quais eixos originais `width`, `height` e `length` ocupam, respectivamente, as dimensões usadas em `x`, `y` e `z`.

### POST `/load-plans/{id}/approve`

Sem body. Retorna `200` com o mesmo `LoadPlanRead`. Exige plano `CALCULATED` sem
rejeições e muda plano/pedidos/histórico atomicamente; pedidos passam a `PLANNED`.

### POST `/load-plans/{id}/recalculate`

Sem body. Retorna `201`. Sempre cria outro plano com
`recalculated_from_id = id` da origem, reutiliza caminhão/pedidos, recarrega os
dados atuais e preserva a origem.

Erros específicos:

- `LOAD_PLAN_NOT_FOUND`.
- `LOAD_PLAN_TRUCK_NOT_FOUND` e `LOAD_PLAN_TRUCK_INACTIVE`.
- `LOAD_PLAN_ORDER_NOT_FOUND` e `LOAD_PLAN_ORDER_NOT_ELIGIBLE`.
- `LOAD_PLAN_PRODUCT_NOT_FOUND`.
- `LOAD_PLAN_VOLUME_LIMIT_EXCEEDED`.
- `INVALID_LOAD_PLAN_INPUT`.
- `LOAD_PLAN_INVALID_STATUS`, `LOAD_PLAN_HAS_REJECTIONS` e
  `LOAD_PLAN_SOURCE_CHANGED`.

### POST `/load-plans/compare-trucks`

Compara de forma transitória os mesmos pedidos em diferentes caminhões. Exige
`LOGISTICS_MANAGER` e não persiste nem cria `LoadPlan`.

```json
{
  "order_ids": ["uuid-do-pedido"],
  "truck_ids": ["uuid-do-caminhao-a", "uuid-do-caminhao-b"]
}
```

Regras de entrada e preflight:

- `order_ids` contém ao menos um UUID e não aceita duplicatas;
- `truck_ids` contém de 2 a 10 UUIDs e não aceita duplicatas;
- todos os pedidos devem existir e estar elegíveis;
- todos os produtos referenciados devem existir;
- todos os caminhões devem existir e estar ativos;
- a soma das quantidades dos pedidos pode materializar no máximo 200 volumes;
- qualquer falha invalida a requisição inteira antes do primeiro cálculo.

Resposta `200`: array direto, com um elemento por caminhão na mesma ordem de
`truck_ids`.

```json
[
  {
    "truck_id": "uuid-do-caminhao-a",
    "internal_volume_cm3": 37440000,
    "used_volume_cm3": 32400000,
    "occupancy_percent": 86.54,
    "total_weight_kg": 5420.0,
    "loaded_count": 28,
    "unloaded_count": 0,
    "rejection_counts": {},
    "algorithm_version": "heuristic-v1"
  },
  {
    "truck_id": "uuid-do-caminhao-b",
    "internal_volume_cm3": 18000000,
    "used_volume_cm3": 15000000,
    "occupancy_percent": 83.33,
    "total_weight_kg": 4200.0,
    "loaded_count": 22,
    "unloaded_count": 6,
    "rejection_counts": {
      "TRUCK_DIMENSIONS_EXCEEDED": 4,
      "TRUCK_WEIGHT_EXCEEDED": 2
    },
    "algorithm_version": "heuristic-v1"
  }
]
```

`rejection_counts` usa os motivos oficiais de `rejection_reason` como chaves e
contagens inteiras positivas como valores; fica vazio quando nenhum volume é
rejeitado. Um caminhão ativo e válido que não comporte toda a carga continua no
array com suas métricas e rejeições. Isso não transforma a resposta em falha.

`CONFIRMADO`: a ordem do array serve somente para correlacionar cada elemento ao
pedido. A resposta não contém vencedor, score, ranking ou recomendação e não
altera a `heuristic-v1`.

Erros específicos:

- `VALIDATION_ERROR`: `order_ids` vazio ou duplicado, `truck_ids` duplicado ou
  com menos de 2 ou mais de 10 elementos, ou UUID malformado;
- `LOAD_PLAN_ORDER_NOT_FOUND` e `LOAD_PLAN_ORDER_NOT_ELIGIBLE`;
- `LOAD_PLAN_PRODUCT_NOT_FOUND`;
- `LOAD_PLAN_TRUCK_NOT_FOUND` e `LOAD_PLAN_TRUCK_INACTIVE`;
- `LOAD_PLAN_VOLUME_LIMIT_EXCEEDED`;
- `INVALID_LOAD_PLAN_INPUT`.

### POST `/load-plans/{id}/explain`

Sem body. Explica um plano persistido sem recalcular, aprovar ou modificar seus
dados. `LOGISTICS_MANAGER` e `ADMIN` podem consultar a explicação de qualquer
plano tecnicamente válido. `CHECKER` pode consultar somente plano `APPROVED` e
`DRIVER` não possui acesso.

Resposta `200` com provider disponível e resposta válida:

```json
{
  "load_plan_id": "uuid-do-plano",
  "source": "AI",
  "explanation": "O plano utilizou 86,54% do volume interno e carregou 28 volumes.",
  "algorithm_version": "heuristic-v1"
}
```

Quando o provider ultrapassa o timeout, está indisponível ou produz resposta
inválida, a mesma operação retorna `200` com explicação determinística e
`source = FALLBACK`. O timeout é configurável e usa 5 segundos por padrão.
`source` aceita exclusivamente `AI` ou `FALLBACK`; `algorithm_version` sempre vem
do plano persistido.

O contexto entregue ao `AIProvider` contém somente métricas, snapshot técnico do
caminhão, posições, rotações, sequência, volumes rejeitados, motivos e
`algorithm_version`. Não contém nome, CPF/CNPJ, telefone ou endereço de cliente,
nem dados pessoais de motorista.

O fallback não encobre erros de autenticação, autorização, recurso inexistente
ou plano tecnicamente inválido. Erros específicos:

- `AUTH_INVALID_TOKEN` ou `AUTH_FORBIDDEN`;
- `LOAD_PLAN_NOT_FOUND`;
- `LOAD_PLAN_EXPLANATION_INVALID_PLAN`: conflito `409`; o plano persistido não
  satisfaz os invariantes necessários para formar o contexto técnico;
- `VALIDATION_ERROR`: UUID de path malformado.

`CONFIRMADO`: o MVP usa uma implementação fake de `AIProvider`, sem rede ou
credencial externa. O adapter concreto será integrado pelo Desenvolvedor 4.

## Carregamento

- `POST /loading-sessions`.
- `GET /loading-sessions/{id}`.
- `PATCH /loading-sessions/{id}/status`.
- `PATCH /loading-sessions/{id}/items/{item_id}`.

`CONFIRMADO`: `POST` recebe `load_plan_id` e cria ou retorna a única sessão do
plano `APPROVED`. A sessão inicia `PENDING`; o status aceita somente
`IN_PROGRESS` e depois `FINISHED`. Cada item recebe `CHECKED` pelo endpoint de
item, e a finalização falha enquanto algum item estiver pendente.

`CONFIRMADO`: `CHECKER` e `LOGISTICS_MANAGER` criam e alteram; `ADMIN`,
`CHECKER` e `LOGISTICS_MANAGER` consultam. Erros específicos:
`LOADING_PLAN_NOT_APPROVED`, `LOADING_SESSION_NOT_FOUND`,
`LOADING_ITEM_NOT_FOUND`, `LOADING_ITEM_SESSION_MISMATCH`,
`LOADING_CHECKLIST_INCOMPLETE` e `LOADING_STATUS_TRANSITION_NOT_ALLOWED`.

## Viagens e entregas

- `GET /trips`.
- `POST /trips`.
- `GET /trips/{id}`.
- `PATCH /trips/{id}/status`.
- `PATCH /deliveries/{id}/status`.

### GET `/trips`

`CONFIRMADO`: a listagem usa `page` 1-based, `page_size` entre 1 e 100 e
`sort_order` `asc` ou `desc`, com os defaults gerais deste contrato. A resposta
usa o envelope `items`, `page`, `page_size`, `total` e `total_pages` e ordena
por `created_at` e `id` na mesma direção.

Cada item contém somente `id`, `load_plan_id`, `driver_id`, `status`,
`started_at`, `finished_at`, `created_at` e `delivery_count`. Nome, telefone,
documento, CNH, cliente, endereço e e-mail não fazem parte da listagem.

`ADMIN` e `LOGISTICS_MANAGER` listam todas as viagens. `DRIVER` lista somente
viagens vinculadas ao próprio `users.driver_id`; ausência de vínculo ou
motorista inexistente/inativo retorna `403 AUTH_FORBIDDEN`. `CHECKER` não
acessa a rota. Não existe filtro público por `driver_id`.

Exemplo de criação por `LOGISTICS_MANAGER`:

```json
{
  "load_plan_id": "uuid-do-plano-aprovado",
  "driver_id": "uuid-do-motorista-ativo"
}
```

Resposta `201`:

```json
{
  "id": "uuid-da-viagem",
  "load_plan_id": "uuid-do-plano-aprovado",
  "driver_id": "uuid-do-motorista-ativo",
  "status": "SCHEDULED",
  "started_at": null,
  "finished_at": null,
  "deliveries": [
    {
      "id": "uuid-da-entrega",
      "trip_id": "uuid-da-viagem",
      "order_id": "uuid-do-pedido",
      "status": "PENDING",
      "sequence": 1,
      "delivered_at": null
    }
  ]
}
```

Corpo das transições:

```json
{
  "status": "IN_ROUTE"
}
```

Regras de autorização:

- somente `LOGISTICS_MANAGER` cria viagem;
- `ADMIN` e `LOGISTICS_MANAGER` consultam qualquer viagem;
- `LOGISTICS_MANAGER` altera qualquer viagem ou entrega;
- `DRIVER` consulta e altera somente viagem atribuída ao seu `driver_id`, desde
  que usuário e motorista continuem ativos;
- `ADMIN` não executa transições operacionais; `CHECKER` não acessa essas rotas.

Regras do contrato:

- criação exige plano `APPROVED`, motorista ativo, pedidos do plano em
  `PLANNED` e ainda sem entrega;
- uma entrega é criada por pedido, com `sequence` contígua 1-based;
- viagem aceita `SCHEDULED -> IN_ROUTE -> FINISHED`;
- entrega aceita `PENDING -> IN_DELIVERY -> DELIVERED` somente durante
  `IN_ROUTE`;
- repetir o status atual é idempotente e não cria novo histórico;
- início exige carregamento finalizado e move todos os pedidos para
  `IN_TRANSIT`;
- conclusão de entrega move o pedido para `DELIVERED`; conclusão da viagem
  exige todas as entregas e pedidos em `DELIVERED`;
- timestamps de início, entrega e fim são retornados em UTC.

Erros específicos:

- `TRIP_NOT_FOUND` e `DELIVERY_NOT_FOUND`;
- `TRIP_LOAD_PLAN_NOT_FOUND`, `TRIP_LOAD_PLAN_NOT_APPROVED` e
  `TRIP_LOAD_PLAN_ALREADY_ASSIGNED`;
- `TRIP_DRIVER_NOT_FOUND` e `TRIP_DRIVER_INACTIVE`;
- `TRIP_ORDER_ALREADY_ASSIGNED`, `TRIP_ORDER_NOT_ELIGIBLE` e
  `TRIP_DELIVERY_SEQUENCE_CONFLICT`;
- `TRIP_LOADING_NOT_FINISHED` e `TRIP_DELIVERIES_NOT_FINISHED`;
- `DELIVERY_TRIP_NOT_IN_ROUTE`;
- `TRIP_STATUS_TRANSITION_NOT_ALLOWED` e
  `DELIVERY_STATUS_TRANSITION_NOT_ALLOWED`.

## Histórico de status

`CONFIRMADO`: criação e mudanças efetivas de pedidos, planos, viagens e entregas
gravam `ORDER`, `LOAD_PLAN`, `TRIP` ou `DELIVERY` em `status_history`, na mesma
transação do agregado.

`CONFIRMADO` por D10: a OC09 não expõe endpoint público para consulta de
histórico.

## Ocorrências

- `POST /occurrences`.
- `GET /trips/{id}/occurrences`.

Exemplo de criação:

```json
{
  "trip_id": "uuid",
  "delivery_id": "uuid",
  "type": "DAMAGED_PRODUCT",
  "description": "Uma caixa foi danificada durante a entrega.",
  "photo_url": "mock://occurrences/photo-1"
}
```

`CONFIRMADO`: `photo_url` permanece opcional. Quando informado, aceita somente
`mock://occurrences/<identificador>`, com identificador alfanumérico que também
pode conter `.`, `_` ou `-`. Referências vazias, HTTP/HTTPS, espaços, query
string e fragmento retornam `422 VALIDATION_ERROR`.

`CONFIRMADO`: a API armazena apenas a referência textual. Não existe endpoint
de upload, armazenamento binário, bucket ou consulta externa de mídia no MVP.

## Mensagens e WhatsApp

- `POST /messages/interpret`: simulador interno disponível somente para usuários
  autenticados com papel `ADMIN` ou `LOGISTICS_MANAGER`.
- `POST /webhooks/whatsapp` permanece fora da v1.0.0; o provider controlado usa
  `POST /messages/interpret`.

`CONFIRMADO`: `driver_phone` identifica o motorista que o operador interno
pretende simular; esse campo não autentica nem autoriza a requisição. O endpoint
não representa autenticação real do WhatsApp. Provider real, webhook e validação
de assinatura permanecem fora deste MVP.

Exemplo de interpretação:

```json
{
  "driver_phone": "+5500000000000",
  "message": "Ja cheguei no cliente"
}
```

Resposta recomendada:

```json
{
  "intent": "ARRIVED",
  "confidence": 0.91,
  "allowed": true,
  "action": "UPDATE_DELIVERY_STATUS"
}
```

`CONFIRMADO`: a resposta inclui `executed`, `confirmation`, `trip_id` e
`delivery_id`. A intenção só vira ação após identificar motorista/viagem/entrega
e o `TripService` validar permissão e estado. Nenhuma regra de viagem ou entrega
é duplicada no módulo de mensagens.

### Notificações automáticas

`CONFIRMADO`: não existe endpoint público específico para notificações. Uma
transição efetiva `SCHEDULED -> IN_ROUTE` realizada por
`PATCH /trips/{id}/status` e um `POST /occurrences` concluído disparam mensagem
determinística para o telefone do motorista da viagem por
`MockWhatsAppProvider`.

`CONFIRMADO`: mensagens automáticas são best-effort e posteriores ao commit.
Falha do mock não muda a resposta nem reverte a operação confirmada. Transição
rejeitada e repetição idempotente não disparam mensagem. Comandos recebidos pelo
simulador mantêm sua confirmação explícita e não recebem um segundo aviso
automático para o mesmo fato.

## Relatórios

- `GET /reports/load-plans/{id}`.
- `GET /reports/trips/{id}`.

`CONFIRMADO`: ambos retornam `application/pdf` com `Content-Disposition:
attachment`. O relatório é gerado em memória a partir dos dados persistidos e
não exige armazenamento permanente na v1.0.0.

## Erros

Formato padrão:

```json
{
  "code": "LOAD_PLAN_INVALID",
  "message": "O plano possui volumes fora dos limites.",
  "details": []
}
```

Regras:

- `code`: string estável em UPPER_SNAKE_CASE.
- `message`: texto claro para interface ou log operacional.
- `details`: lista com campos, IDs ou motivos de validação.
- `VALIDATION_ERROR`: payload, path ou query não atende ao schema; usa status `422` e identifica os campos inválidos em `details`.
- `INTERNAL_SERVER_ERROR`: falha inesperada; usa status `500`, mensagem pública genérica e `details` vazio, sem expor informações internas.
- `CONFIRMADO`: o OpenAPI referencia o mesmo schema `ErrorResponse` para os erros públicos documentados em cada operação.

Mapeamento recomendado:

- `400`: entrada inválida ou regra de negócio violada.
- `401`: autenticação ausente ou inválida.
- `403`: perfil sem permissão.
- `404`: entidade não encontrada.
- `409`: conflito de estado, duplicidade ou versão.
- `422`: validação de schema.
- `500`: erro inesperado.

## Segurança de API

- Somente `GET /health`, `GET /ready` e `POST /api/v1/auth/login` são públicos.
- Todos os demais endpoints de negócio exigem o cookie de sessão e aplicam a
  matriz de `docs/04-regras-negocio.md`.
- `POST`, `PUT`, `PATCH` e `DELETE` exigem `Origin` presente na lista exata de
  CORS. Operações autenticadas nesses métodos também exigem `X-CSRF-Token`.
- `CONFIRMADO`: com `APP_ENV=local`, `/docs`, `/docs/oauth2-redirect`, `/redoc` e `/openapi.json` ficam disponíveis. Com `APP_ENV=production` ou sem a variável, essas rotas não são registradas e retornam `404`.
- Senhas nunca retornam na API.
- Tokens e segredos nunca aparecem em logs.
- Dados pessoais devem ser minimizados em respostas de listagem.
- Endpoints que alteram status devem registrar histórico.
- Integrações externas devem ser autenticadas quando saírem do modo mock.

`CONFIRMADO`: CORS permite credenciais somente para as origens exatas de
`BACKEND_CORS_ORIGINS` e expõe `X-CSRF-Token` ao frontend próprio.

`CONFIRMADO`: todas as respostas da aplicação usam `Cache-Control: no-store`,
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`, política restritiva de permissões e CSP que
impede framing. Em `production`, também usam `Strict-Transport-Security` por um
ano com `includeSubDomains`.

`CONFIRMADO`: novos hashes de senha usam Argon2id com memória de 19 MiB, duas
iterações e paralelismo 1. PBKDF2 legado é aceito apenas para migração gradual
após autenticação válida.

`CONFIRMADO`: a autorização por perfil segue `ADR-004`; acesso não listado é negado.

`PENDENTE DE DEFINIÇÃO`: autenticação própria e validação de assinatura do webhook de WhatsApp devem ser aprovadas antes de uma integração externa real.
