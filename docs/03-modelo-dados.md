# Modelo de dados inicial

## OC84 — notificações operacionais duráveis

`CONFIRMADO`: a Issue #127 e a ADR-037 autorizam notificações internas reais
com saída WhatsApp exclusivamente mock. Antes da OC84, a base `c9b634c` não
armazenava notificações duráveis. `status_history` e `occurrences` comprovam os fatos,
mas não armazenam uma notificação nem o resultado de sua simulação.
`external_commands` deduplica comandos, não notificações ou tentativas de saída.
Reutilizar essas tabelas como histórico de envio mudaria seu significado.

`CONFIRMADO`: implementação autorizada pela revisão de Rennan na PR #226,
comentário 6289881953. Tabela `operational_notifications`, módulo notifications,
migration `20261020_0025` sobre `20261016_0024`. Sem backfill fictício.

| Campo | Tipo | Finalidade e restrição |
| --- | --- | --- |
| `id` | UUID | PK, gerada pelo servidor |
| `event_type` | varchar(32) | Catálogo fechado `TRIP_STARTED` / `OCCURRENCE_REGISTERED` |
| `status_history_id` | UUID nullable | FK `status_history.id` RESTRICT, somente para início efetivo `TRIP: SCHEDULED -> IN_ROUTE` |
| `occurrence_id` | UUID nullable | FK `occurrences.id` RESTRICT, somente para ocorrência registrada |
| `trip_id` | UUID | FK `trips.id` RESTRICT; recurso operacional de origem |
| `recipient_driver_id` | UUID | FK `drivers.id` RESTRICT; motorista da viagem no momento do fato |
| `created_at` | timestamptz | UTC do servidor, na transação do fato |
| `mock_status` | varchar(24) | `NOT_ATTEMPTED`, `ATTEMPT_CLAIMED`, `SIMULATED`, `FAILED` ou `NO_RECIPIENT`; sem semântica de entrega externa |
| `correlation_id` | UUID | Contexto técnico gerado pelo servidor, sem payload ou segredo |
| `claimed_at` | timestamptz nullable | Commit do claim, separado do resultado |
| `completed_at` | timestamptz nullable | Finalização local; não comprova entrega externa |

`CONFIRMADO`: a existência da linha confirmada representa o registro interno;
não adicionar `read_at`, preferências ou estado lida/não lida da OC103. Não copiar
telefone, texto, descrição de ocorrência, assinatura, subject, dados de sessão ou
identificador bruto de integração. `recipient_driver_id` preserva o destinatário
operacional atual mesmo quando não existe conta `users` vinculada; isso **não
concede acesso HTTP** nem aprova inferir um futuro destinatário da central.

`CONFIRMADO`: CHECK exige exatamente a origem correspondente ao `event_type`;
CHECK fecha `mock_status`. Dois índices UNIQUE parciais protegem
`(event_type, status_history_id, recipient_driver_id)` quando o histórico não é
nulo e `(event_type, occurrence_id, recipient_driver_id)` quando a ocorrência
não é nula. Índice `(trip_id, created_at, id)` atende rastreamento técnico. UUIDs
das origens vêm exclusivamente dos services públicos donos; a validação de
proveniência verifica viagem, transição e destinatário na mesma transação.
FK isolada não comprova esses vínculos semânticos.

`CONFIRMADO`: triggers PostgreSQL validam viagem/transição efetiva da origem,
viagem da ocorrência e destinatário operacional no INSERT. A identidade registrada
é imutável; alterações de estado permitem apenas NOT_ATTEMPTED → ATTEMPT_CLAIMED
→ SIMULATED/FAILED/NO_RECIPIENT, com timestamps coerentes. FKs RESTRICT conservam
histórico. Downgrade recusa perda de notificações já registradas.

## OC87 — necessidade multi-caminhão

`RECOMENDAÇÃO`: ADR-028 propõe quatro tabelas no módulo load_planning. Migration
20261007_0015 sucede 20261007_0014; planos/itens legados não são reescritos.

- `load_distributions`: id UUID, status fechado, created_by FK users RESTRICT,
  created_at UTC. Necessidade completa; nenhuma seleção automática de frota.
- `load_distribution_orders`: PK (distribution_id,order_id), FKs RESTRICT,
  active boolean; índice único parcial order_id WHERE active para ownership.
- `load_distribution_parts`: id UUID estável, distribution_id FK RESTRICT,
  load_plan_id FK RESTRICT único, status PENDING/APPROVED/CANCELED. UNIQUE
  (id,distribution_id) para FK composta dos volumes. Recálculo troca somente a
  referência ao plano, preservando sua cadeia recalculated_from_id.
- `load_distribution_volumes`: PK (distribution_id,order_item_id,volume_index),
  order_id/product_id com FK composta para proveniência em order_items,
  snapshot_quantity positivo, volume_index 1..snapshot_quantity, part_id com
  FK composta para a mesma distribuição, active boolean. FK composta para
  load_distribution_orders. Índice único parcial (order_item_id,volume_index)
  WHERE active impede duas necessidades reivindicarem a mesma unidade.

`RECOMENDAÇÃO`: triggers diferidas verificam a necessidade exata, proveniência,
quantidades, volumes de cada plano e estados no COMMIT. Caminhões das partes
são distintos, derivados dos planos. Histórico amplia catálogo com
LOAD_DISTRIBUTION/LOAD_DISTRIBUTION_PART; nenhuma nova máquina de estados ORDER.
Retenção histórica e cancelamento/reprocessamento estão na ADR-028.

## OC80 — evidências de entrega

`RECOMENDAÇÃO`: ADR-027 propõe delivery_evidences no módulo deliveries, sem mudar
Delivery/receipt OC78. Migration 20261007_0014 sucede 20261006_0013.

| Campo | Tipo | Regra |
|---|---|---|
| id | UUID | PK e chave opaca de storage, gerada pelo servidor |
| delivery_id | UUID | FK deliveries RESTRICT |
| receipt_id | UUID | FK status_history RESTRICT; conclusão validada pelo service |
| recorded_by | UUID | FK users RESTRICT, ator do servidor |
| event_id | UUID | identidade idempotente, UNIQUE com recorded_by |
| kind | varchar(16) | PHOTO / SIGNATURE |
| media_type | varchar(32) | image/png / image/jpeg detectado nos bytes |
| size_bytes | integer | 1–5242880 |
| sha256 | varchar(64) | checksum do binário |
| fingerprint | varchar(64) | hash de entrega/tipo/bytes para conflito |
| status | varchar(16) | ACTIVE / REVOKED |
| recorded_at | timestamptz | servidor |
| revoked_at | timestamptz nullable | presente somente REVOKED |
| revoked_by | UUID nullable | FK users RESTRICT; presente somente REVOKED |

`RECOMENDAÇÃO`: índice (delivery_id, recorded_at, id) para consulta paginada;
CHECKs de tipo/formato/tamanho e consistência de revogação. Metadados não guardam
payload, caminho, URL, segredo ou nome de recebedor. Retenção/remoção na ADR-027.

## OC79 — registro de comandos externos

`RECOMENDAÇÃO`: estrutura proposta pela Issue #122 e ADR-026, sujeita à revisão.
`external_commands` pertence ao módulo `external_commands`; não guarda payload,
assinatura, subject, telefone ou chave secreta.

| Campo | Tipo | Regra |
|---|---|---|
| id | UUID | PK, receipt gerado pelo servidor |
| integration_id | varchar(64) | identidade configurada no servidor |
| event_hash | varchar(64) | SHA-256 do event_id |
| fingerprint | varchar(64) | SHA-256 dos bytes assinados |
| user_id | UUID | FK users, ator resolvido pelo servidor |
| command | varchar(32) | START_TRIP / START_DELIVERY / FINISH_DELIVERY |
| expires_at | timestamptz | limite exclusivo de validade |
| completed_at | timestamptz, nullable | preenchido antes do commit externo |

`RECOMENDAÇÃO`: UNIQUE `(integration_id, event_hash)` serializa duplicatas.
Hashes têm CHECK de formato hexadecimal de 64 caracteres; command tem CHECK
fechado. Linha sem completed_at existe somente dentro da transação: falha remove
também efeitos de domínio. Não há limpeza automática. Migration `20261006_0012`
sucede `20260830_0011`, mantendo um único head.

## Estado atual

`CONFIRMADO`: o repositório possui models SQLAlchemy e migrations para `users`,
`auth_sessions`, `auth_login_throttles`, `customers`, `drivers`, `trucks`,
`products`, `orders`, `order_items`, `status_history`, `audit_events`, `load_plans`,
`load_plan_orders`, `load_plan_items`, `trips` e `deliveries`. As tabelas de
autenticação foram aprovadas por D18 e `ADR-020`; viagens e entregas seguem
D07 a D10, D21 e `ADR-022`.

`CONFIRMADO`: `loading_sessions` e `loading_session_items` possuem models e
migration no fluxo de carregamento da v1.0.0.

`CONFIRMADO`: `occurrences` possui model e migration desde a OC41.

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
- `driver_id`: UUID, FK opcional para `drivers.id`.
- `active`: booleano, obrigatório.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `uq_users__email`.
- `fk_users__drivers` com `ON DELETE RESTRICT`.
- `uq_users__driver_id`.
- `ix_users__role` `RECOMENDAÇÃO`.

`CONFIRMADO` por D21 e `ADR-022`: somente um usuário pode se vincular a cada
motorista; vínculo não nulo exige `role = DRIVER`. Alterar o vínculo revoga as
sessões do usuário na mesma transação.

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

`CONFIRMADO`: o acesso operacional do perfil `DRIVER` exige `users.driver_id`
igual ao motorista da viagem e ambos, usuário e motorista, ativos.

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
- `priority`: texto, obrigatório, com valores permitidos `LOW`, `NORMAL`, `HIGH`
  e `URGENT`, normalizado em maiúsculas pela API.
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

`CONFIRMADO`: `status` aceita `PENDING`, `IN_PROGRESS` e `FINISHED`.
`started_at` existe a partir de `IN_PROGRESS`; `finished_at` existe somente em
`FINISHED`, nunca antes do início.

### `loading_session_items`

Checklist materializado dos volumes posicionados no plano.

- `id`: UUID, PK.
- `loading_session_id`: UUID, FK para `loading_sessions.id`, obrigatório.
- `load_plan_item_id`: UUID, FK para `load_plan_items.id`, obrigatório.
- `status`: texto obrigatório, `PENDING` ou `CHECKED`.

Índices e constraints:

- `fk_loading_session_items__loading_sessions`.
- `fk_loading_session_items__load_plan_items`.
- `uq_loading_session_items__session_plan_item`.
- índices de `loading_session_id` e `load_plan_item_id`.
- `ck_loading_session_items__status_allowed`.

### `trips`

Viagens vinculadas ao plano carregado.

- `id`: UUID, PK.
- `load_plan_id`: UUID, FK para `load_plans.id`, obrigatório, único.
- `driver_id`: UUID, FK para `drivers.id`, obrigatório.
- `status`: texto ou enum, obrigatório.
- `started_at`: timestamptz UTC.
- `finished_at`: timestamptz UTC.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `fk_trips__load_plans`.
- `fk_trips__drivers`.
- `uq_trips__load_plan_id`.
- `ix_trips__driver_id`.
- `ix_trips__status`.
- `ck_trips__status_allowed`.
- `ck_trips__timestamps_consistent`.

`CONFIRMADO`: `status` aceita `SCHEDULED`, `IN_ROUTE` e `FINISHED`.
`started_at` é obrigatório a partir de `IN_ROUTE`; `finished_at` existe somente
em `FINISHED` e não pode anteceder `started_at`.

`CONFIRMADO`: `created_at` permite ordenar a listagem de viagens de forma
determinística, usando `id` como desempate na mesma direção.

### `deliveries`

Entregas planejadas dentro de uma viagem.

- `id`: UUID, PK.
- `trip_id`: UUID, FK para `trips.id`, obrigatório.
- `order_id`: UUID, FK para `orders.id`, obrigatório.
- `distribution_part_id`: UUID nullable, FK RESTRICT para `load_distribution_parts.id` (OC90).
- `status`: texto ou enum, obrigatório.
- `sequence`: inteiro, obrigatório.
- `delivered_at`: timestamptz UTC.

Índices e constraints:

- `fk_deliveries__trips`.
- `fk_deliveries__orders`.
- `fk_deliveries__load_distribution_parts`.
- `ix_deliveries__trip_id`.
- `ix_deliveries__order_id`.
- `ix_deliveries__status`.
- `uq_deliveries__legacy_order`: índice único parcial por order_id quando parte NULL.
- `uq_deliveries__part_order`: UNIQUE distribution_part_id/order_id.
- `uq_deliveries__trip_order`.
- `uq_deliveries__trip_sequence`.
- `ck_deliveries__status_allowed`.
- `ck_deliveries__sequence_positive`.
- `ck_deliveries__completion_consistent`.

`CONFIRMADO`: `status` aceita `PENDING`, `IN_DELIVERY` e `DELIVERED`. Cada pedido
legado gera no máximo uma entrega. Na OC90, cada parte que transporta volumes
do pedido gera sua própria entrega, com contexto validado por triggers. `sequence` é 1-based, positiva, contígua e
única na viagem; sua ordenação deriva de `order_items.delivery_sequence` e do
UUID do pedido como desempate. Todos os itens de um pedido devem informar a
mesma sequência. `delivered_at` existe se e somente se o status é `DELIVERED`.

### Projeção do comprovante operacional — OC78

`CONFIRMADO` pela ADR-024: reutilizar `deliveries`, `trips` e o histórico da
conclusão como base do comprovante operacional. Não há tabela, coluna, índice ou
constraint nova. O `id` do comprovante é o UUID do único histórico `DELIVERY`,
`IN_DELIVERY -> DELIVERED`, da entrega consultada, com `changed_by` obrigatório
para essa projeção. Vínculos vêm da entrega/viagem; horários e responsável vêm
dos registros persistidos. O modelo físico aprovado permanece inalterado.

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
- `ck_status_history__entity_type_allowed`.

`CONFIRMADO`: `entity_type`, `old_status` e `new_status` são normalizados em maiúsculas pela camada de schema/service.

`CONFIRMADO` por D10 e `ADR-022`: `entity_type` aceita somente `ORDER`,
`LOAD_PLAN`, `TRIP` e `DELIVERY`. A OC09 não expõe consulta pública desse
histórico.

### `audit_events` — OC97

Auditoria administrativa somente leitura, complementar a `status_history`.

- `id`: UUID, PK.
- `event_type`: catálogo fechado do tipo de evento administrativo.
- `entity_type`: catálogo fechado da entidade auditada.
- `entity_id`: UUID do registro afetado.
- `actor_id`: UUID, FK obrigatória para `users.id`.
- `changed_fields`: nomes dos campos alterados, em ordem determinística e sem valores.
- `created_at`: timestamptz UTC, obrigatório.

Índices e constraints:

- `fk_audit_events__users`.
- `ix_audit_events__entity`.
- `ix_audit_events__actor_id`.
- `ix_audit_events__created_at`.
- `ck_audit_events__event_type_allowed`.
- `ck_audit_events__entity_type_allowed`.

`CONFIRMADO` pela OC97: a primeira entrega registra somente `USER_CREATED` e
`USER_UPDATED`, ambos com `entity_type = USER`. A tabela não persiste valores de
senha, token, sessão, e-mail, nome ou payload completo; `changed_fields` contém
apenas nomes de campos para informar o que foi alterado sem replicar dado sensível.

`CONFIRMADO`: o histórico operacional existente continua em `status_history`.
A consulta da OC97 agrega as duas fontes sem modificar nem apagar registros.

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
- `drivers` 1:0..1 `users` por `users.driver_id`.
- `trips` 1:N `deliveries`.
- `orders` 1:0..1 `deliveries` no legado; 1:N por partes na OC90, no máximo uma por parte/pedido.
- `trips` 1:N `occurrences`.
- `deliveries` 1:N `occurrences`.
- `users` 1:N `status_history` por `changed_by`.
- `users` 1:N `audit_events` por `actor_id`.

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

`CONFIRMADO`: a migration `20261006_0013` cria `audit_events` para a OC97 e sucede a `20261006_0012` da OC79.

`CONFIRMADO`: a migration `20260804_0004` cria `load_plans`,
`load_plan_orders` e `load_plan_items` para a integração da `OC20`.

`CONFIRMADO`: a migration `20260809_0007` cria o vínculo opcional e único
`users.driver_id`; `20260809_0008` fecha o catálogo de `status_history` e cria
`trips` e `deliveries` para a `OC09`.

`CONFIRMADO`: a migration `20260830_0011` adiciona `trips.created_at` com valor
gerado pelo PostgreSQL e retrocompatibilidade para viagens existentes.

## Observação

O modelo é inicial. Qualquer mudança estrutural relevante deve ser registrada por migration e por ADR quando alterar uma decisão arquitetural, unidade, contrato público ou regra permanente.

## OC105 — ciclo de vida dos cadastros

`CONFIRMADO`: clientes, produtos, caminhões e motoristas usam `active` não nulo,
com default `true`. `false` significa arquivado; conflitos operacionais continuam
sendo calculados separadamente. A migration `20261008_0016` adiciona o campo
somente a clientes e produtos, preservando dados existentes como ativos.
Unicidades permanecem globais, inclusive para arquivados; FKs e histórico não
são removidos. O catálogo de `audit_events` aceita `RECORD_ARCHIVED` e
`RECORD_REACTIVATED` para CUSTOMER, PRODUCT, TRUCK e DRIVER.

## OC99 — múltiplos endereços por cliente

`CONFIRMADO`: `customer_addresses` pertence a customers: UUID `id`, FK
`customer_id` RESTRICT, `label`, `address` (texto até 255), `city`, `state`,
`postal_code` opcional (8 dígitos), `active`, `is_primary` e `created_at` UTC.
Há UNIQUE parcial de principal por cliente, CHECK principal implica ativo,
índice por cliente e UNIQUE `(id, customer_id)` para proveniência composta.
Cada cliente com endereços ativos mantém um principal pelo service, serializado
pelo bloqueio da linha do cliente. Arquivar o principal promove o ativo mais
antigo; sem ativos, os campos legados mantêm o último endereço conhecido.

`CONFIRMADO`: `customers.address/city/state` permanecem como projeção do
principal para compatibilidade. Create/PATCH legado sincroniza a projeção e o
principal na mesma transação. Backfill cria um principal por cliente sem alterar
os campos existentes. Pedidos antigos não recebem vínculo inferido ao cadastro.

`CONFIRMADO`: orders adiciona `customer_address_id` opcional, FK composta
`(customer_address_id, customer_id)` → customer_addresses e
`delivery_address_snapshot` JSONB opcional. Seleção copia endereço, cidade, UF,
CEP e rótulo; `delivery_address` continua o texto contratado até 255 caracteres.
Backfill de pedidos copia apenas seu próprio texto, sem presumir cidade/UF
históricas. Alterar/arquivar o cadastro não modifica snapshot nem pedido.
Auditoria administrativa inclui CUSTOMER_ADDRESS e eventos próprios de criação,
edição, arquivamento e reativação, sem conteúdo do endereço no evento.

## OC100 — manutenção da frota

`CONFIRMADO`: trucks acrescenta odometer_km, next_service_at (UTC) e
next_service_km opcionais. Quilometragens são inteiros não negativos; informação
omitida não inventa valores e odômetro informado não pode diminuir.
truck_maintenances pertence a trucks, com UUID, truck_id RESTRICT, kind
PREVENTIVE/CORRECTIVE, starts_at/ends_at UTC (fim opcional, maior que início),
description, workshop/notes opcionais, cost opcional não negativo, odometer_km,
completion_odometer_km, next_service_at/km opcionais, closed_at e created_at.
Índice por truck_id/starts_at atende histórico e consulta de período.
Manutenção aberta bloqueia em [starts_at, ends_at), ou sem fim indefinidamente;
closed_at encerra o bloqueio. Histórico e auditoria permanecem sem DELETE.
O catálogo administrativo aceita TRUCK_MAINTENANCE, MAINTENANCE_CREATED,
MAINTENANCE_CLOSED e TRUCK_ODOMETER_UPDATED. Lock do caminhão serializa
manutenção, quilometragem e reserva operacional; não altera active da OC105.

## OC101 — documentos dos caminhões

`RECOMENDAÇÃO`: `truck_documents`: id UUID PK, truck_id UUID FK RESTRICT,
kind varchar(16) limitado a CRLV/LICENSING/INSURANCE, reference varchar(120)
não vazio, issued_at/expires_at UTC opcionais (expires > issued quando ambas
presentes), file_reference UUID opaco opcional, superseded_at UTC opcional,
created_at UTC obrigatório default now. Índice único parcial (truck_id, kind)
onde superseded_at IS NULL; índice (truck_id, created_at) para histórico.
`truck_document_policies`: id UUID PK, truck_id FK RESTRICT, kind mesmo catálogo,
required boolean obrigatório default false; unique (truck_id, kind).
Auditoria acrescenta entidades TRUCK_DOCUMENT/TRUCK_DOCUMENT_POLICY e eventos
TRUCK_DOCUMENT_CREATED/TRUCK_DOCUMENT_RENEWED/TRUCK_DOCUMENT_POLICY_UPDATED.
Migration sequencial 20261009_0019, down_revision 20261009_0018. ADR-031.

## OC102 — documentos de motoristas

`RECOMENDAÇÃO`: drivers acrescenta license_expires_at UTC opcional.
DriverDocumentType: driver_document_types (id UUID PK, code varchar32 unique
não vazio, name varchar120 não vazio); CNH é tipo nativo com UUID reservado.
DriverDocument: driver_documents (id UUID PK, driver_id FK RESTRICT,
document_type_id FK RESTRICT, reference varchar120 não vazio, category varchar8
opcional, issued_at/expires_at UTC opcionais, superseded_at UTC opcional,
created_at UTC default now). Check expires > issued; índice único parcial
(driver_id, document_type_id) onde superseded_at IS NULL; índice histórico
(driver_id, created_at).
DriverDocumentPolicy: driver_document_policies (id UUID PK, driver_id FK
RESTRICT, document_type_id FK RESTRICT, required boolean default false,
allowed_categories JSONB array obrigatório default []), unique por motorista/tipo.
Auditoria: DRIVER_DOCUMENT, DRIVER_DOCUMENT_POLICY, DRIVER_DOCUMENT_TYPE e
DRIVER_DOCUMENT_CREATED/RENEWED/POLICY_UPDATED/TYPE_APPROVED. ADR-032.

`CONFIRMADO` (OC102): driver_documents também possui legacy_backfill boolean
obrigatório default false, exclusivo do backfill e da proteção de downgrade.
Policy tem CHECK PostgreSQL jsonb_typeof(allowed_categories)='array'.

## OC110 — anexos operacionais

`CONFIRMADO`: contrato aditivo da Issue #157, detalhado na ADR-033. Tabela
`operational_attachments`: UUID `id`, exatamente uma FK RESTRICT entre `order_id`,
`trip_id`, `delivery_id`, `occurrence_id`; `recorded_by`/`revoked_by` referenciam
usuários com RESTRICT. `event_id` com UNIQUE por autor permite retry sem outro
blob. `media_type` PNG/JPEG, `size_bytes` 1–5242880, `sha256` e `fingerprint`
64 caracteres, `recorded_at` UTC e estado ACTIVE/REVOKED com revogação consistente.
Índices por recurso/data/id suportam consulta paginada. Nenhum caminho ou URL é
persistido; chave do adapter é o UUID interno. FK impede órfãos fora do service.
Auditoria adiciona ATTACHMENT_REGISTERED/ATTACHMENT_REVOKED para ATTACHMENT,
na mesma transação; remoção nunca exclui metadata/histórico nem bytes confirmados.
Migration 20261009_0021 encadeada em 20261009_0020. Downgrade recusa perda de
anexos ou auditoria, inclusive revogados.

## OC104 — importação controlada de cadastros

`CONFIRMADO`: Issue #151 e ADR-034 definem `registration_imports`: id UUID,
entity_type customers/products/trucks/drivers, recorded_by FK RESTRICT users,
event_id UUID UNIQUE com recorded_by, sha256/fingerprint (64 hex), recorded_at UTC,
status PROCESSING/COMPLETED/REJECTED, row_count/created_count/rejected_count
limitados a 0–1000, errors/records JSONB arrays. Records associa número da linha
a UUID criado; errors contém linha/campo/código/mensagem sem valor pessoal.
CHECK protege conservação dos totais, resultado completo ou rejeição total e
tipos dos JSONs. Índices por entidade/data/id e ator suportam histórico paginado.
Não persiste nome, CSV original nem valores dos cadastros. PROCESSING só existe
dentro da transação de confirmação; rollback remove tentativa não confirmada.
AuditEvent adiciona IMPORT_COMPLETED/IMPORT_REJECTED para REGISTRATION_IMPORT,
na mesma transação do resultado. Migration 20261009_0022 → 20261009_0021;
downgrade recusa histórico ou auditoria OC104 para evitar perda.

## OC91 — company_profiles

`CONFIRMADO`: cadastro institucional singleton standalone, conforme ADR-035.
UUID local fixo `00000000-0000-0000-0000-000000000091`, PK e CHECK singleton;
`legal_name`/`display_name` obrigatórios, `cnpj`/`phone`/`email`/`logo_reference`
opcionais, `created_at`/`updated_at` UTC. Não representa tenant e não possui
vínculos dos agregados logísticos. Eventos COMPANY_PROFILE_CREATED/UPDATED
registram somente nomes de campos e ator, na mesma transação.

## OC112 — Perfis locais e permissões

`CONFIRMADO`: migration `20261016_0024` sobre `20261009_0023`:

- `access_profiles`: UUID, nome/nome normalizado único, descrição, active, versão
  positiva e created_at UTC. Nome normalizado é validado também no PostgreSQL.
- `access_permissions`: catálogo fechado, PK code e unique(code, delegable).
- `access_profile_permissions`: PK(profile_id, permission_code), FKs restritivas,
  delegable=true com CHECK e FK composta; não admite permissão reservada.
- `users.custom_profile_id`: FK opcional/indexada/restritiva. CHECK exige
  exatamente role=CUSTOM com perfil preenchido, ou papel fixo com perfil nulo.
  Usuários existentes mantêm papel, UUID e acesso, sem reclassificação.
- Auditoria inclui ACCESS_PROFILE e PROFILE_CREATED/PROFILE_UPDATED, somente
  nomes de campos. Não existe exclusão HTTP de perfis.

`CONFIRMADO`: rollback estrutural é recusado enquanto usuários CUSTOM ou eventos
históricos de perfil existirem, para evitar perda silenciosa de acesso/histórico.

## OC103 — destinatários e preferências da central

`CONFIRMADO`: ADR-042; migration 20261020_0026 sobre 20261020_0025.
`notification_recipients`: PK composta notification_id/user_id (UUID), FKs RESTRICT
para operational_notifications/users, created_at UTC obrigatório (default now),
read_at UTC opcional. Índices user_id/created_at/notification_id e parcial user_id
para não lidas. Trigger protege identidade/criação e primeira leitura imutáveis.
`notification_preferences`: PK user_id/category, FK RESTRICT users, enabled boolean
obrigatório default true, updated_at UTC default now. CHECK category em
TRIPS/OCCURRENCES/SECURITY e SECURITY sempre habilitada. Sem telefone/texto/segredo.
Backfill só cria associações das contas elegíveis no corte. Downgrade com qualquer
associação/preferência é recusado; fatos da OC84 são preservados integralmente.

## OC109 — Outbox persistente (ADR-043)

`CONFIRMADO`: outbox_events pertence a notifications: id UUID, notification_id FK
RESTRICT/UNIQUE, channel WHATSAPP_MOCK, event_type, contract_version=1, correlation_id,
idempotency_key UNIQUE, status, attempt_count por ciclo, generation monotônica,
next_attempt_at/lease_expires_at UTC, last_error_code sanitizado, created_at/updated_at.
Índices por status/agendamento e created_at/id. outbox_attempts registra UUID,
outbox_event_id FK RESTRICT, generation UNIQUE por evento, started_at/finished_at,
result e error_code; outbox_retry_commands fixa UUID idempotente, evento, ator FK
RESTRICT e data. Auditoria acrescenta OUTBOX_REPROCESSED/OUTBOX_EVENT. Sem payload
de texto/telefone, sem exclusão automática. Migration 20261020_0027.


## OC90 — entrega por perna física

`CONFIRMADO`: a revisão `20261020_0028` sucede `20261020_0027`. Delivery recebe
`distribution_part_id` UUID nullable, FK RESTRICT para `load_distribution_parts`.
NULL preserva o legado: índice único parcial `uq_deliveries__legacy_order`
por `order_id WHERE distribution_part_id IS NULL`. Para distribuição, a UNIQUE
`uq_deliveries__part_order` limita uma entrega por parte/pedido. Permanecem as
unicidades de trip/order, trip/sequence e trips/load_plan_id.

`CONFIRMADO`: trigger de contexto serializa atribuições pelo pedido e valida
parte atual/aprovada, distribuição aprovada, plano da viagem e existência de
volume do pedido nessa parte. Impede mistura legado/distribuição e distribuições
distintas para o mesmo pedido. Contexto da entrega e plano da viagem com entregas
são imutáveis; estrutura/status da distribuição com entregas também ficam
protegidos no banco. Identidades continuam somente no planejamento, sem cópia
ou renumeração em Delivery. As FKs e CHECKs anteriores permanecem vigentes.

`CONFIRMADO`: upgrade associa entregas antigas de partes operacionais únicas à
parte já persistida. Downgrade aborta se existir qualquer entrega com contexto
de parte: não remove vínculos, entregas nem auditoria para restaurar o schema
anterior. Sem esse estado operacional, o downgrade restaura a unicidade global.
Ver ADR-044 (proposta para revisão da equipe).

`CONFIRMADO` (OC90): upgrade revalida entregas antigas com a mesma trigger de
contexto usada por escritas futuras. Vínculo antigo inconsistente aborta o upgrade
transacional, preservando schema/dados anteriores; não há correção silenciosa.


`CONFIRMADO` (correção de integridade OC90): a primeira LoadingSession persistida
marca a imutabilidade operacional do LoadPlan; a existência de Trip também é
verificada defensivamente, incluindo planos legados. A função PostgreSQL
`protect_operated_load_plan()` protege UPDATE/DELETE da linha inteira de
`load_plans` e INSERT/UPDATE/DELETE de `load_plan_orders` e `load_plan_items`.
Os triggers `protect_operated_load_plans`, `protect_operated_load_plan_orders` e
`protect_operated_load_plan_items` rejeitam mudanças com SQLSTATE 23514 e
constraint `ck_load_plans__operational_snapshot`. UPDATE sem mudança real é
permitido. Ambos os pais são verificados em reatribuições; não há lista parcial
de colunas editáveis, cópia de volumes ou alteração do contrato HTTP.

`CONFIRMADO`: criação de LoadingSession serializa pelo LoadPlan FOR UPDATE,
recarrega snapshots/itens do identity map após o lock e só então materializa o
checklist e adquire o caminhão. Trip create já adquire plano antes de caminhão,
motorista e pedidos. Escrita direta de filho pode já possuir lock da tupla antes
da trigger; por isso a guarda tenta pais em UUID crescente com FOR UPDATE NOWAIT.
Contenção rejeita a mutação com a mesma constraint e mensagem para repetir a
transação, inclusive antes da operação. Não espera por um pai que possa estar
aguardando a FK do checklist nesse filho, evitando esse ciclo. A guarda não
bloqueia sessão, viagem, distribuição ou pedido; apenas consulta evidências
persistidas. Planejamento sem evidência operacional conserva criação, aprovação
e reprocessamento permitidos. Constraints e locks de contexto/distribuição
existentes permanecem; o congelamento do snapshot físico começa no loading,
antes da primeira entrega que protege a estrutura da distribuição.
