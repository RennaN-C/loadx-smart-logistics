# Contratos iniciais da API

Este documento é o contrato combinado entre backend, frontend, algoritmo e integrações. Alterações devem ser discutidas, versionadas e refletidas em testes.

## Convenções

- `CONFIRMADO`: prefixo oficial da API de negócio: `/api/v1`.
- `CONFIRMADO`: health check atual fica em `/health`, fora do prefixo.
- `CONFIRMADO`: JSON usa campos em snake_case.
- `RECOMENDAÇÃO`: caminhos usam kebab-case quando tiverem mais de uma palavra, como `/load-plans`.
- `RECOMENDAÇÃO`: endpoints de listagem devem preparar paginação futura, mesmo que o MVP comece simples.
- `RECOMENDAÇÃO`: filtros usam query params em snake_case.
- `PENDENTE DE DEFINIÇÃO`: padrão final de paginação, ordenação e filtros.
- `CONFIRMADO`: em atualizações parciais, campos omitidos permanecem inalterados; `null` só é aceito para campos anuláveis no modelo de dados.

## Autenticação

Endpoints públicos:

- `POST /auth/login`.

Endpoint disponível para qualquer usuário autenticado:

- `GET /auth/me`.

Exemplo de login:

```json
{
  "email": "admin@example.test",
  "password": "senha-local"
}
```

Resposta recomendada:

```json
{
  "access_token": "jwt",
  "token_type": "bearer"
}
```

Para acessar `/auth/me`, envie:

```text
Authorization: Bearer <access_token>
```

Erros específicos:

- `AUTH_INVALID_CREDENTIALS`: e-mail ou senha inválidos.
- `AUTH_INVALID_TOKEN`: token ausente, inválido, expirado ou usuário inexistente.
- `AUTH_USER_INACTIVE`: usuário inativo.
- `AUTH_FORBIDDEN`: usuário autenticado sem permissão para a ação.

`CONFIRMADO`: `POST /auth/register` foi removido do contrato por `D03` e `ADR-004`. O primeiro `ADMIN` é criado por comando administrativo local; os usuários seguintes são criados por `ADMIN` em `POST /users`.

`CONFIRMADO`: depois das migrations e antes de expor a API, o bootstrap é executado em `backend` com `python -m app.modules.auth.bootstrap` ou, pela raiz, com `docker compose run --rm backend python -m app.modules.auth.bootstrap`. A senha é lida de forma oculta e o comando recusa execução quando já existe qualquer usuário.

`CONFIRMADO`: ausência ou invalidade de autenticação retorna `401 AUTH_INVALID_TOKEN`; autenticação válida sem permissão retorna `403 AUTH_FORBIDDEN`.

`CONFIRMADO`: após a `OC51-G`, todos os endpoints de negócio atualmente implementados exigem autenticação e aplicam a matriz aprovada.

`PENDENTE DE DEFINIÇÃO`: tempo final de expiração, refresh token e política de bloqueio de login.

## Saúde

### GET `/health`

```json
{
  "status": "ok",
  "service": "loadx-api"
}
```

## Usuários

- `GET /users`.
- `POST /users`.
- `GET /users/{id}`.
- `PATCH /users/{id}`.

Regras do contrato aprovado:

- Todas as rotas de `/users` exigem perfil `ADMIN`.
- Campos públicos retornados: `id`, `name`, `email`, `role`, `active` e `created_at`.
- `password_hash` nunca é retornado.
- `role` aceita `ADMIN`, `CHECKER`, `DRIVER` e `LOGISTICS_MANAGER`.
- `email` é normalizado para minúsculas.
- `role` é normalizado para maiúsculas.
- `password` deve ter no mínimo 8 caracteres na entrada.

Erros específicos:

- `USER_NOT_FOUND`: usuário não encontrado.
- `USER_EMAIL_ALREADY_EXISTS`: e-mail já cadastrado.
- `USER_LAST_ACTIVE_ADMIN_REQUIRED`: alteração deixaria o sistema sem `ADMIN` ativo.

`CONFIRMADO`: não existe cadastro público. O primeiro `ADMIN` usa bootstrap local e, depois, usuários são criados somente por `ADMIN`.

## Caminhões

- `GET /trucks`.
- `POST /trucks`.
- `GET /trucks/{id}`.
- `PATCH /trucks/{id}`.

Regras de autorização:

- `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem usar `GET`.
- Somente `LOGISTICS_MANAGER` pode usar `POST` e `PATCH`.
- `DRIVER` não acessa essas rotas enquanto não existir vínculo aprovado.

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
- `DRIVER` não acessa essas rotas enquanto não existir vínculo aprovado.

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

## Motoristas

- `GET /drivers`.
- `POST /drivers`.
- `GET /drivers/{id}`.
- `PATCH /drivers/{id}`.

Regras de autorização:

- `ADMIN` e `LOGISTICS_MANAGER` podem usar `GET`.
- Somente `LOGISTICS_MANAGER` pode usar `POST` e `PATCH`.
- `CHECKER` e `DRIVER` não acessam essas rotas.

## Pedidos

- `GET /orders`.
- `POST /orders`.
- `GET /orders/{id}`.
- `PATCH /orders/{id}`.
- `PATCH /orders/{id}/status`.

Regras de autorização:

- `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem usar `GET`.
- Somente `LOGISTICS_MANAGER` pode usar `POST` e `PATCH`.
- `DRIVER` não acessa essas rotas enquanto não existir vínculo aprovado.

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

- `POST /orders` cria o pedido com `status = "DRAFT"`.
- `PATCH /orders/{id}` aceita alteração de `customer_id`, `priority`,
  `delivery_address`, `expected_delivery_at` e, quando `items` for enviado,
  substitui o conjunto somente em `DRAFT` e se nenhum item estiver referenciado
  por plano. O payload rejeita `status` e campos desconhecidos.
- `PATCH /orders/{id}/status` recebe `{"status": "READY"}` e aplica somente a
  matriz de transições manuais de D04. Aprovação de plano, início de viagem e
  conclusão de entrega mantêm seus próprios casos de uso.
- `status` aceita `DRAFT`, `READY`, `PLANNED`, `IN_TRANSIT`, `DELIVERED` e `CANCELED`.
- `priority` é texto obrigatório e é normalizado para maiúsculas.
- `expected_delivery_at` deve vir com timezone e é normalizado para UTC.
- O pedido deve possuir pelo menos um item.
- `quantity` e `delivery_sequence` devem ser maiores que zero.
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

- Somente `LOGISTICS_MANAGER` usa criação, aprovação e recálculo.
- `ADMIN` e `LOGISTICS_MANAGER` consultam qualquer plano.
- `CHECKER` consulta somente plano `APPROVED`.
- `DRIVER` não acessa enquanto não existir vínculo operacional aprovado.

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
do cálculo. `Decimal` permanece no schema; a decisão separada sobre representar
Decimal como número ou string JSON não é alterada pela OC20.

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

`CONFIRMADO`: `POST /load-plans/compare-trucks` pertence à OC21 e não é exposto
pela integração da OC20.

## Carregamento

- `POST /loading-sessions`.
- `GET /loading-sessions/{id}`.
- `PATCH /loading-sessions/{id}/status`.
- `PATCH /loading-sessions/{id}/items/{item_id}`.

## Viagens e entregas

- `POST /trips`.
- `GET /trips/{id}`.
- `PATCH /trips/{id}/status`.
- `PATCH /deliveries/{id}/status`.

## Histórico de status

`CONFIRMADO`: mudanças de status devem gravar registros em `status_history`.

`PENDENTE DE DEFINIÇÃO`: endpoint público para consulta de histórico ainda não está aprovado.

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

## Mensagens e WhatsApp

- `POST /messages/interpret`.
- `POST /webhooks/whatsapp` `PENDENTE DE DEFINIÇÃO`.

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

`CONFIRMADO`: a resposta da IA deve ser validada por schema e convertida em ação apenas quando a intenção for permitida.

## Relatórios

- `GET /reports/load-plans/{id}`.
- `GET /reports/trips/{id}`.

`PENDENTE DE DEFINIÇÃO`: formato final de download, headers e armazenamento temporário do PDF.

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

- Somente `GET /health` e `POST /api/v1/auth/login` são públicos.
- Todos os demais endpoints de negócio exigem Bearer token e aplicam a matriz de `docs/04-regras-negocio.md`.
- `CONFIRMADO`: com `APP_ENV=local`, `/docs`, `/docs/oauth2-redirect`, `/redoc` e `/openapi.json` ficam disponíveis. Com `APP_ENV=production` ou sem a variável, essas rotas não são registradas e retornam `404`.
- Senhas nunca retornam na API.
- Tokens e segredos nunca aparecem em logs.
- Dados pessoais devem ser minimizados em respostas de listagem.
- Endpoints que alteram status devem registrar histórico.
- Integrações externas devem ser autenticadas quando saírem do modo mock.

`CONFIRMADO`: a autorização por perfil segue `ADR-004`; acesso não listado é negado.

`PENDENTE DE DEFINIÇÃO`: autenticação própria e validação de assinatura do webhook de WhatsApp devem ser aprovadas antes de uma integração externa real.
