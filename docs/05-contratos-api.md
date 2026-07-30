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

## Autenticação

Endpoints previstos:

- `POST /auth/register`.
- `POST /auth/login`.
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

`PENDENTE DE DEFINIÇÃO`: tempo de expiração, refresh token e política de bloqueio de login.

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

`PENDENTE DE DEFINIÇÃO`: se cadastro público de usuário será permitido ou se usuários serão criados apenas por administrador.

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

## Motoristas

- `GET /drivers`.
- `POST /drivers`.
- `GET /drivers/{id}`.
- `PATCH /drivers/{id}`.

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

Mapeamento recomendado:

- `400`: entrada inválida ou regra de negócio violada.
- `401`: autenticação ausente ou inválida.
- `403`: perfil sem permissão.
- `404`: entidade não encontrada.
- `409`: conflito de estado, duplicidade ou versão.
- `422`: validação de schema.
- `500`: erro inesperado.

## Segurança de API

- Senhas nunca retornam na API.
- Tokens e segredos nunca aparecem em logs.
- Dados pessoais devem ser minimizados em respostas de listagem.
- Endpoints que alteram status devem registrar histórico.
- Integrações externas devem ser autenticadas quando saírem do modo mock.

`PENDENTE DE DEFINIÇÃO`: esquema final de autorização por perfil e proteção do webhook de WhatsApp.
