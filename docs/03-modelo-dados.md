# Modelo de dados inicial

## Estado atual

`CONFIRMADO`: o repositório possui models SQLAlchemy e migrations para `users`, `customers`, `drivers`, `trucks`, `products`, `orders` e `order_items`.

`PENDENTE DE DEFINIÇÃO`: load_plans, load_plan_orders, load_plan_items, loading_sessions, trips, deliveries, occurrences e status_history ainda não possuem models/migrations.

`CONFIRMADO`: este documento é o contrato inicial para a criação do banco. Qualquer mudança estrutural deve ser registrada por migration e documentada aqui.

`CONFIRMADO`: nomes físicos de tabelas, colunas, models, rotas e campos de API ficam em inglês, mesmo quando o documento-base usa nomes em português.

## Padrões físicos do banco

- Tabelas em plural snake_case: `trucks`, `order_items`, `load_plan_items`.
- Chave primária padrão: `id` UUID.
- Chave estrangeira: `<entity>_id`, como `truck_id` e `customer_id`.
- Dimensões: sufixo `_cm`.
- Peso: sufixo `_kg`.
- Datas e horários: sufixo `_at`, armazenados em UTC.
- Booleanos: nomes afirmativos, como `active`, `fragile`, `stackable`, `placed`.
- Valores monetários não fazem parte do MVP.
- Dados sensíveis não devem aparecer em seeds.

`RECOMENDAÇÃO`: usar nomes estáveis para constraints:

- `pk_<table>`;
- `fk_<table>__<referenced_table>`;
- `uq_<table>__<columns>`;
- `ix_<table>__<columns>`;
- `ck_<table>__<rule>`.

## Entidades do MVP

### `users`

Usuários internos do sistema.

- `id`: UUID, PK.
- `name`: texto, obrigatório.
- `email`: texto, obrigatório, único.
- `password_hash`: texto, obrigatório.
- `role`: texto ou enum, obrigatório.
- `active`: booleano, obrigatório.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `uq_users__email`.
- `ix_users__role` `RECOMENDAÇÃO`.

### `customers`

Clientes ou destinatários usados em pedidos e entregas.

- `id`: UUID, PK.
- `name`: texto, obrigatório.
- `document`: texto, CPF ou CNPJ, obrigatório.
- `phone`: texto.
- `address`: texto, obrigatório no MVP.
- `city`: texto, obrigatório.
- `state`: texto, obrigatório.
- `notes`: texto opcional.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `uq_customers__document` `RECOMENDAÇÃO`.
- `ix_customers__name` `RECOMENDAÇÃO`.

### `drivers`

Motoristas vinculados a viagens.

- `id`: UUID, PK.
- `name`: texto, obrigatório.
- `document`: texto, CPF, obrigatório conforme documento-base.
- `phone`: texto, obrigatório para WhatsApp simulado/controlado.
- `license_number`: texto, obrigatório.
- `license_category`: texto.
- `active`: booleano, obrigatório.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `uq_drivers__document` `RECOMENDAÇÃO`.
- `uq_drivers__license_number` `RECOMENDAÇÃO`.
- `ix_drivers__phone` `RECOMENDAÇÃO`.

### `trucks`

Caminhões e sua capacidade interna.

- `id`: UUID, PK.
- `plate`: texto, obrigatório, único.
- `model`: texto, obrigatório.
- `internal_width_cm`: inteiro ou numérico, obrigatório, maior que zero.
- `internal_height_cm`: inteiro ou numérico, obrigatório, maior que zero.
- `internal_length_cm`: inteiro ou numérico, obrigatório, maior que zero.
- `max_weight_kg`: numérico, obrigatório, maior que zero.
- `active`: booleano, obrigatório.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `uq_trucks__plate`.
- `ck_trucks__dimensions_positive`.
- `ck_trucks__max_weight_positive`.

### `products`

Produtos cadastrados com suas características físicas. Quantidade não pertence ao cadastro do produto.

- `id`: UUID, PK.
- `code`: texto, obrigatório.
- `name`: texto, obrigatório.
- `description`: texto opcional.
- `width_cm`: inteiro ou numérico, obrigatório, maior que zero.
- `height_cm`: inteiro ou numérico, obrigatório, maior que zero.
- `length_cm`: inteiro ou numérico, obrigatório, maior que zero.
- `weight_kg`: numérico, obrigatório, maior que zero.
- `fragile`: booleano, obrigatório.
- `stackable`: booleano, obrigatório.
- `rotation_allowed`: booleano, obrigatório.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `uq_products__code` `RECOMENDAÇÃO`.
- `ix_products__name` `RECOMENDAÇÃO`.
- `ck_products__dimensions_positive`.
- `ck_products__weight_positive`.

### `orders`

Pedidos de entrega.

- `id`: UUID, PK.
- `customer_id`: UUID, FK para `customers.id`, obrigatório.
- `status`: texto, obrigatório, valores permitidos atuais `DRAFT`, `READY`, `PLANNED`, `IN_TRANSIT`, `DELIVERED` e `CANCELED`.
- `priority`: texto, obrigatório, normalizado em maiúsculas pela API.
- `delivery_address`: texto, obrigatório.
- `expected_delivery_at`: timestamptz UTC.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `fk_orders__customers`.
- `ix_orders__customer_id`.
- `ix_orders__status`.
- `ix_orders__expected_delivery_at` `RECOMENDAÇÃO`.
- `ck_orders__status_allowed`.

### `order_items`

Itens de pedido e quantidades solicitadas.

- `id`: UUID, PK.
- `order_id`: UUID, FK para `orders.id`, obrigatório.
- `product_id`: UUID, FK para `products.id`, obrigatório.
- `quantity`: inteiro, obrigatório, maior que zero.
- `delivery_sequence`: inteiro, obrigatório para orientar carregamento e descarga.

Índices e constraints:

- `fk_order_items__orders`.
- `fk_order_items__products`.
- `ix_order_items__order_id`.
- `ix_order_items__product_id`.
- `ck_order_items__quantity_positive`.
- `ck_order_items__delivery_sequence_positive`.

### `load_plans`

Resultado calculado para uma carga.

- `id`: UUID, PK.
- `truck_id`: UUID, FK para `trucks.id`, obrigatório.
- `status`: texto ou enum, obrigatório.
- `occupancy_percent`: numérico, de 0 a 100.
- `total_weight_kg`: numérico, obrigatório.
- `loaded_count`: inteiro, obrigatório.
- `unloaded_count`: inteiro, obrigatório.
- `algorithm_version`: texto, obrigatório.
- `created_at`: timestamptz UTC, obrigatório.
- `approved_at`: timestamptz UTC opcional.

Índices e constraints:

- `fk_load_plans__trucks`.
- `ix_load_plans__truck_id`.
- `ix_load_plans__status`.
- `ck_load_plans__occupancy_percent_range`.
- `ck_load_plans__counts_non_negative`.

### `load_plan_orders`

Relacionamento N:N entre planos e pedidos.

- `load_plan_id`: UUID, FK para `load_plans.id`, obrigatório.
- `order_id`: UUID, FK para `orders.id`, obrigatório.

Índices e constraints:

- PK composta por `load_plan_id` e `order_id`.
- `fk_load_plan_orders__load_plans`.
- `fk_load_plan_orders__orders`.
- `ix_load_plan_orders__order_id`.

### `load_plan_items`

Volumes individuais posicionados ou rejeitados pelo plano.

- `id`: UUID, PK.
- `load_plan_id`: UUID, FK para `load_plans.id`, obrigatório.
- `order_item_id`: UUID, FK para `order_items.id`, obrigatório.
- `volume_index`: inteiro, obrigatório, identifica a unidade dentro da quantidade do item.
- `position_x_cm`: numérico, obrigatório quando `placed = true`.
- `position_y_cm`: numérico, obrigatório quando `placed = true`.
- `position_z_cm`: numérico, obrigatório quando `placed = true`.
- `used_width_cm`: numérico, obrigatório quando `placed = true`.
- `used_height_cm`: numérico, obrigatório quando `placed = true`.
- `used_length_cm`: numérico, obrigatório quando `placed = true`.
- `rotation_code`: texto, obrigatório quando `placed = true`.
- `loading_sequence`: inteiro, obrigatório quando `placed = true`.
- `placed`: booleano, obrigatório.
- `rejection_reason`: texto obrigatório quando `placed = false`.

Índices e constraints:

- `fk_load_plan_items__load_plans`.
- `fk_load_plan_items__order_items`.
- `ix_load_plan_items__load_plan_id`.
- `ix_load_plan_items__order_item_id`.
- `uq_load_plan_items__plan_item_volume`.
- `ck_load_plan_items__placed_or_rejected` `RECOMENDAÇÃO`.

### `loading_sessions`

Checklist e estado do carregamento físico.

- `id`: UUID, PK.
- `load_plan_id`: UUID, FK para `load_plans.id`, obrigatório, único.
- `status`: texto ou enum, obrigatório.
- `started_at`: timestamptz UTC.
- `finished_at`: timestamptz UTC.

Índices e constraints:

- `fk_loading_sessions__load_plans`.
- `uq_loading_sessions__load_plan_id`.
- `ix_loading_sessions__status`.

### `trips`

Viagens vinculadas ao plano carregado.

- `id`: UUID, PK.
- `load_plan_id`: UUID, FK para `load_plans.id`, obrigatório, único.
- `driver_id`: UUID, FK para `drivers.id`, obrigatório.
- `status`: texto ou enum, obrigatório.
- `started_at`: timestamptz UTC.
- `finished_at`: timestamptz UTC.

Índices e constraints:

- `fk_trips__load_plans`.
- `fk_trips__drivers`.
- `uq_trips__load_plan_id`.
- `ix_trips__driver_id`.
- `ix_trips__status`.

### `deliveries`

Entregas planejadas dentro de uma viagem.

- `id`: UUID, PK.
- `trip_id`: UUID, FK para `trips.id`, obrigatório.
- `order_id`: UUID, FK para `orders.id`, obrigatório.
- `status`: texto ou enum, obrigatório.
- `sequence`: inteiro, obrigatório.
- `delivered_at`: timestamptz UTC.

Índices e constraints:

- `fk_deliveries__trips`.
- `fk_deliveries__orders`.
- `ix_deliveries__trip_id`.
- `ix_deliveries__order_id`.
- `ix_deliveries__status`.
- `uq_deliveries__trip_sequence` `RECOMENDAÇÃO`.

### `occurrences`

Ocorrências registradas durante carregamento, viagem ou entrega.

- `id`: UUID, PK.
- `trip_id`: UUID, FK para `trips.id`, obrigatório quando relacionada a viagem.
- `delivery_id`: UUID, FK para `deliveries.id`, opcional.
- `type`: texto ou enum, obrigatório.
- `description`: texto, obrigatório.
- `photo_url`: texto opcional.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `fk_occurrences__trips`.
- `fk_occurrences__deliveries`.
- `ix_occurrences__trip_id`.
- `ix_occurrences__delivery_id`.
- `ix_occurrences__type`.
- `ck_occurrences__description_not_empty` `RECOMENDAÇÃO`.

### `status_history`

Histórico auditável de mudanças de status.

- `id`: UUID, PK.
- `entity_type`: texto, obrigatório.
- `entity_id`: UUID, obrigatório.
- `old_status`: texto opcional.
- `new_status`: texto, obrigatório.
- `changed_by`: UUID, FK para `users.id`, opcional.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `fk_status_history__users`.
- `ix_status_history__entity`.
- `ix_status_history__created_at`.

## Relacionamentos principais

- `customers` 1:N `orders`.
- `orders` 1:N `order_items`.
- `products` 1:N `order_items`.
- `trucks` 1:N `load_plans`.
- `load_plans` N:N `orders` por `load_plan_orders`.
- `load_plans` 1:N `load_plan_items`.
- `order_items` 1:N `load_plan_items`.
- `load_plans` 1:1 `loading_sessions`.
- `load_plans` 1:1 `trips`.
- `drivers` 1:N `trips`.
- `trips` 1:N `deliveries`.
- `orders` 1:N `deliveries`.
- `trips` 1:N `occurrences`.
- `deliveries` 1:N `occurrences`.
- `users` 1:N `status_history` por `changed_by`.

## Volumes

`CONFIRMADO`: o MVP fala em produtos e volumes.

`SUPOSIÇÃO TÉCNICA`: no modelo atual, volumes individuais são materializados em `load_plan_items` a partir de `order_items.quantity`; não existe uma tabela separada `volumes`.

`DECISÃO NECESSÁRIA`: o documento-base lista uma tabela `volumes`. A equipe deve decidir se cria uma tabela própria para volumes antes do planejamento ou se mantém a geração determinística por `order_items.quantity` e persistência em `load_plan_items`.

## Migrations

- Toda mudança estrutural deve nascer em model SQLAlchemy e migration Alembic.
- A migration deve acompanhar testes mínimos e atualização deste documento.
- Não enviar SQL solto como fonte oficial.
- Não alterar staging manualmente como solução definitiva.
- Migrations devem ser pequenas e relacionadas a uma ocorrência.

`CONFIRMADO`: a configuração oficial do Alembic fica em `backend/alembic.ini` e `backend/migrations/env.py`. Os comandos estão documentados em `backend/migrations/README.md`.

`CONFIRMADO`: a migration `20260730_0002` cria `orders` e `order_items` para a ocorrência `OC08`.

## Observação

O modelo é inicial. Qualquer mudança estrutural relevante deve ser registrada por migration e por ADR quando alterar uma decisão arquitetural, unidade, contrato público ou regra permanente.
