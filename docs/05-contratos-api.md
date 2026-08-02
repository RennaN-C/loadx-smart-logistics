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

`RISCO IDENTIFICADO`: após a `OC51-E`, usuários, clientes e motoristas estão protegidos, mas caminhões, produtos e pedidos ainda aguardam as próximas partes da `OC51` para receber a proteção aprovada.

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
- `PATCH /orders/{id}` aceita alteração de `customer_id`, `status`, `priority`, `delivery_address`, `expected_delivery_at` e, quando `items` for enviado, substitui o conjunto de itens do pedido.
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

## Planos de carga

### POST `/load-plans`

```json
{
  "truck_id": "uuid",
  "order_ids": ["uuid"]
}
```

Resposta resumida:

```json
{
  "id": "uuid",
  "status": "CALCULATED",
  "occupancy_percent": 86.4,
  "total_weight_kg": 5420,
  "loaded_count": 28,
  "unloaded_count": 2,
  "algorithm_version": "heuristic-v1"
}
```

### GET `/load-plans/{id}/visualization`

```json
{
  "truck": {
    "width_cm": 240,
    "height_cm": 260,
    "length_cm": 600
  },
  "items": [
    {
      "id": "uuid",
      "product_name": "Caixa A",
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
      "id": "uuid",
      "product_name": "Caixa B",
      "rejection_reason": "TRUCK_DIMENSIONS_EXCEEDED"
    }
  ]
}
```

Outras rotas:

- `GET /load-plans/{id}`.
- `POST /load-plans/{id}/approve`.
- `POST /load-plans/{id}/recalculate`.
- `POST /load-plans/compare-trucks` `PENDENTE DE DEFINIÇÃO`.

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
- Documentação interativa e OpenAPI ficam disponíveis no ambiente local; em produção devem ser desabilitados ou protegidos.
- Senhas nunca retornam na API.
- Tokens e segredos nunca aparecem em logs.
- Dados pessoais devem ser minimizados em respostas de listagem.
- Endpoints que alteram status devem registrar histórico.
- Integrações externas devem ser autenticadas quando saírem do modo mock.

`CONFIRMADO`: a autorização por perfil segue `ADR-004`; acesso não listado é negado.

`PENDENTE DE DEFINIÇÃO`: autenticação própria e validação de assinatura do webhook de WhatsApp devem ser aprovadas antes de uma integração externa real.
