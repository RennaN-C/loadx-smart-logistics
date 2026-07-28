# Contratos iniciais da API

Prefixo oficial: `/api/v1`

Este documento é o contrato combinado entre backend, frontend, algoritmo e integrações. Alterações devem ser discutidas e versionadas.

## Saúde

### GET `/health`

```json
{"status": "ok", "service": "loadx-api"}
```

## Caminhões

- `GET /trucks`
- `POST /trucks`
- `GET /trucks/{id}`
- `PATCH /trucks/{id}`

Exemplo de criação:

```json
{
  "plate": "ABC1D23",
  "model": "Baú médio",
  "internal_width_cm": 240,
  "internal_height_cm": 260,
  "internal_length_cm": 600,
  "max_weight_kg": 8000
}
```

## Produtos

- `GET /products`
- `POST /products`
- `GET /products/{id}`
- `PATCH /products/{id}`

## Pedidos

- `GET /orders`
- `POST /orders`
- `GET /orders/{id}`
- `PATCH /orders/{id}`

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
  ]
}
```

Outras rotas:

- `GET /load-plans/{id}`
- `POST /load-plans/{id}/approve`
- `POST /load-plans/{id}/recalculate`

## Carregamento

- `POST /loading-sessions`
- `PATCH /loading-sessions/{id}/status`
- `PATCH /loading-sessions/{id}/items/{item_id}`

## Viagens e entregas

- `POST /trips`
- `PATCH /trips/{id}/status`
- `GET /trips/{id}`
- `PATCH /deliveries/{id}/status`

## Ocorrências

- `POST /occurrences`
- `GET /trips/{id}/occurrences`

## Mensagens

- `POST /messages/interpret`

A resposta da IA deve ser validada por schema e convertida em ação apenas quando a intenção for permitida.

## Erros

Formato padrão:

```json
{
  "code": "LOAD_PLAN_INVALID",
  "message": "O plano possui volumes fora dos limites.",
  "details": []
}
```
