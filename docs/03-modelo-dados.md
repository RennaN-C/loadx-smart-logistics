# Modelo de dados inicial

## Estado atual

`CONFIRMADO`: o repositório possui models SQLAlchemy e migrations para `users`,
`customers`, `drivers`, `trucks`, `products`, `orders`, `order_items`,
`status_history`, `load_plans`, `load_plan_orders` e `load_plan_items`.

`CONFIRMADO` por D18 e `ADR-020`: `auth_sessions` e
`auth_login_throttles` integram o modelo aprovado e possuem models e migrations
Alembic na OC60.

`PENDENTE DE DEFINIÇÃO`: `loading_sessions`, `trips`, `deliveries` e
`occurrences` ainda não possuem models/migrations.

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

### `auth_sessions`

Sessões opacas e revogáveis do frontend próprio.

- `id`: UUID, PK.
- `user_id`: UUID, FK obrigatória para `users.id`.
- `token_hash`: texto hexadecimal de 64 caracteres, obrigatório e único.
- `created_at`: timestamptz UTC, obrigatório.
- `last_seen_at`: timestamptz UTC, obrigatório.
- `idle_expires_at`: timestamptz UTC, obrigatório.
- `absolute_expires_at`: timestamptz UTC, obrigatório.
- `revoked_at`: timestamptz UTC, opcional.

Índices e constraints:

- `fk_auth_sessions__users` com `ON DELETE CASCADE`.
- `uq_auth_sessions__token_hash`.
- `ix_auth_sessions__user_id`.
- `ix_auth_sessions__idle_expires_at`.
- `ck_auth_sessions__absolute_expiration_after_creation`.

`CONFIRMADO`: o identificador bruto da sessão e o token CSRF não são persistidos.
O CSRF é derivado por HMAC do identificador bruto recebido no cookie.

### `auth_login_throttles`

Contadores duráveis de falhas de login por conta e por endereço IP.

- `id`: UUID, PK.
- `scope`: texto obrigatório, `ACCOUNT` ou `IP`.
- `subject_hash`: HMAC-SHA-256 hexadecimal de 64 caracteres, obrigatório.
- `failed_count`: inteiro obrigatório, maior ou igual a zero.
- `blocked_until`: timestamptz UTC, opcional.
- `updated_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `uq_auth_login_throttles__scope_subject_hash`.
- `ix_auth_login_throttles__blocked_until`.
- `ck_auth_login_throttles__scope_allowed`.
- `ck_auth_login_throttles__failed_count_non_negative`.

`CONFIRMADO`: e-mail e IP brutos não são persistidos nessa tabela.

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

`RISCO IDENTIFICADO`: não existe relacionamento entre `users` e `drivers` no modelo aprovado. Até que uma ocorrência futura aprove esse vínculo, um usuário `DRIVER` não pode receber acesso baseado em motorista, viagem ou entrega própria.

### `trucks`

Caminhões e sua capacidade interna.

- `id`: UUID, PK.
- `plate`: texto, obrigatório, único.
- `model`: texto, obrigatório.
- `internal_width_cm`: inteiro, obrigatório, maior que zero.
- `internal_height_cm`: inteiro, obrigatório, maior que zero.
- `internal_length_cm`: inteiro, obrigatório, maior que zero.
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
- `width_cm`: inteiro, obrigatório, maior que zero.
- `height_cm`: inteiro, obrigatório, maior que zero.
- `length_cm`: inteiro, obrigatório, maior que zero.
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
- `uq_order_items__id_order_product`, chave candidata para validar a proveniência
  composta dos volumes persistidos.
- `ck_order_items__quantity_positive`.
- `ck_order_items__delivery_sequence_positive`.

### `load_plans`

Resultado calculado para uma carga.

- `id`: UUID, PK.
- `truck_id`: UUID, FK para `trucks.id`, obrigatório.
- `recalculated_from_id`: UUID, FK autorreferente opcional para o plano de origem.
- `status`: `VARCHAR`, obrigatório, limitado a `CALCULATED`, `APPROVED` e
  `REJECTED`.
- `truck_snapshot_plate` e `truck_snapshot_model`: textos obrigatórios.
- `truck_snapshot_internal_width_cm`, `truck_snapshot_internal_height_cm` e
  `truck_snapshot_internal_length_cm`: inteiros positivos.
- `truck_snapshot_max_weight_kg`: numérico positivo com duas casas.
- `internal_volume_cm3`: inteiro positivo igual ao produto das dimensões do
  snapshot.
- `used_volume_cm3`: inteiro entre zero e o volume interno.
- `occupancy_percent`: `Decimal` de 0 a 100, com duas casas e `ROUND_HALF_UP`, calculado somente sobre o volume dos itens colocados.
- `total_weight_kg`: numérico não negativo, obrigatório, soma somente dos volumes colocados.
- `loaded_count`: inteiro, obrigatório.
- `unloaded_count`: inteiro, obrigatório.
- `algorithm_version`: texto, obrigatório; versão inicial `heuristic-v1`.
- `created_at`: timestamptz UTC, obrigatório.
- `approved_at`: timestamptz UTC opcional.

Índices e constraints:

- `fk_load_plans__trucks`.
- `fk_load_plans__load_plans` para `recalculated_from_id`, com exclusão restrita.
- `ix_load_plans__truck_id`.
- `ix_load_plans__recalculated_from_id`.
- `ix_load_plans__status`.
- `ck_load_plans__occupancy_percent_range`.
- `ck_load_plans__counts_valid`.
- `ck_load_plans__status_metrics_consistent`.
- `ck_load_plans__approval_consistent`.

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
- `order_id`: UUID, FK para `orders.id`, obrigatório.
- `order_item_id`: UUID, FK para `order_items.id`, obrigatório.
- `product_id`: UUID, FK para `products.id`, obrigatório.
- `volume_index`: inteiro positivo iniciado em `1`, obrigatório, identifica a unidade dentro da quantidade do item.
- `order_item_snapshot_quantity` e
  `order_item_snapshot_delivery_sequence`: inteiros positivos usados no cálculo.
- `product_snapshot_code`, `product_snapshot_name`, dimensões originais, peso e
  flags `fragile`, `stackable` e `rotation_allowed`: fotografia obrigatória do
  produto usado no cálculo.
- `position_x_cm`: inteiro não negativo, obrigatório quando `placed = true`.
- `position_y_cm`: inteiro não negativo, obrigatório quando `placed = true`.
- `position_z_cm`: inteiro não negativo, obrigatório quando `placed = true`.
- `used_width_cm`: inteiro positivo, obrigatório quando `placed = true`.
- `used_height_cm`: inteiro positivo, obrigatório quando `placed = true`.
- `used_length_cm`: inteiro positivo, obrigatório quando `placed = true`.
- `rotation_code`: texto opcional, obrigatório quando `placed = true` e nulo quando `placed = false`, com um dos valores `XYZ`, `XZY`, `YXZ`, `YZX`, `ZXY` ou `ZYX`.
- `loading_sequence`: inteiro, obrigatório quando `placed = true`.
- `placed`: booleano, obrigatório.
- `rejection_reason`: texto obrigatório quando `placed = false`, com um dos valores `TRUCK_DIMENSIONS_EXCEEDED`, `TRUCK_WEIGHT_EXCEEDED`, `NON_STACKABLE_SUPPORT`, `FRAGILE_SUPPORT_WEIGHT_EXCEEDED`, `INSUFFICIENT_SUPPORT`, `COLLISION` ou `NO_VALID_POSITION`.

Índices e constraints:

- `fk_load_plan_items__load_plans`.
- `fk_load_plan_items__orders`.
- `fk_load_plan_items__order_items`.
- `fk_load_plan_items__products`.
- `fk_load_plan_items__load_plan_orders`, sobre `load_plan_id` e `order_id`.
- `fk_load_plan_items__order_item_provenance`, sobre `order_item_id`, `order_id`
  e `product_id`.
- `ix_load_plan_items__load_plan_id`.
- `ix_load_plan_items__order_id`.
- `ix_load_plan_items__order_item_id`.
- `ix_load_plan_items__product_id`.
- `uq_load_plan_items__plan_item_volume`, sobre `load_plan_id`, `order_item_id` e `volume_index`.
- `ck_load_plan_items__volume_index_positive`.
- `ck_load_plan_items__rotation_code_allowed`, aceitando nulo para unidade rejeitada.
- `uq_load_plan_items__plan_loading_sequence`.
- `ck_load_plan_items__rejection_reason_allowed`, aceitando nulo para unidade
  colocada e somente o catálogo da `ADR-011` para unidade rejeitada.
- checks de coordenadas não negativas e dimensões usadas positivas.
- `ck_load_plan_items__rotation_permission_consistent` e
  `ck_load_plan_items__rotation_dimensions_consistent`.
- `ck_load_plan_items__placed_or_rejected`.

`CONFIRMADO`: todas as FKs históricas das três tabelas usam exclusão restrita.
Em particular, um `order_item` referenciado não pode ser removido por uma
substituição posterior do conjunto de itens do pedido.

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

`CONFIRMADO`: `entity_type`, `old_status` e `new_status` são normalizados em maiúsculas pela camada de schema/service.

`PENDENTE DE DEFINIÇÃO`: lista final de `entity_type` permitidos.

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

`CONFIRMADO`: conforme `ADR-005`, volumes individuais são gerados
deterministicamente a partir de `order_items.quantity`, usam identidade
`(order_item_id, volume_index)` com índice iniciado em `1` e são persistidos em
`load_plan_items`.

`CONFIRMADO`: o MVP não terá tabela separada `volumes`.

## Migrations

- Toda mudança estrutural deve nascer em model SQLAlchemy e migration Alembic.
- A migration deve acompanhar testes mínimos e atualização deste documento.
- Não enviar SQL solto como fonte oficial.
- Não alterar staging manualmente como solução definitiva.
- Migrations devem ser pequenas e relacionadas a uma ocorrência.

`CONFIRMADO`: a configuração oficial do Alembic fica em `backend/alembic.ini` e `backend/migrations/env.py`. Os comandos estão documentados em `backend/migrations/README.md`.

`CONFIRMADO`: a migration `20260730_0002` cria `orders` e `order_items` para a ocorrência `OC08`.

`CONFIRMADO`: a migration `20260730_0003` cria `status_history` para a ocorrência `OC10`.

`CONFIRMADO`: a migration `20260804_0004` cria `load_plans`,
`load_plan_orders` e `load_plan_items` para a integração da `OC20`.

## Observação

O modelo é inicial. Qualquer mudança estrutural relevante deve ser registrada por migration e por ADR quando alterar uma decisão arquitetural, unidade, contrato público ou regra permanente.
