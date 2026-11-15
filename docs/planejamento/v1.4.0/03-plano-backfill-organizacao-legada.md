# Plano de backfill seguro da organização legada

- **Data:** 15/11/2026
- **Status:** planejamento técnico; ainda não executado.
- **Base de referência:** `desenvolvimento` em `af70acdb`.
- **Matriz:** PR #454 — `docs/planejamento/v1.4.0/02-matriz-ownership-53-tabelas.md`.
- **Fundação:** PR #449, migration `20261114_0036`, ainda não integrada.
- **Issue de execução documental:** #457.
- **Organização legada:** `00000000-0000-4000-8000-000000000301`.
- **CompanyProfile legado:** `00000000-0000-0000-0000-000000000091`.

## 1. Objetivo e limites

Definir uma execução reproduzível para associar os dados atuais à organização legada, comprovar integridade e permitir rollback sem perda de histórico.

O plano cobre:

1. Baseline de contagens antes de qualquer alteração.
2. Pré-validação dos dados usados pela migration 0036.
3. Backfill das 40 tabelas ORG/HERDADO.
4. Tratamento específico das três tabelas MISTO e da tabela LEGADO.
5. Verificação de órfãos, relações polimórficas, atores, unicidades e FKs compostas.
6. Reconciliação antes/depois, quarentena e rollback.

**Não executar este plano no Render, Neon ou em qualquer banco remoto nesta etapa.** Os primeiros ensaios devem usar clone isolado PostgreSQL 16, com backup restaurável e sem dados de clientes expostos.

A feature flag multiempresa permanece desligada. Não habilitar segunda organização, onboarding, convite operacional ou seletor. Este documento não autoriza migrations de scoping, merge, deploy ou release.

## 2. Inventário e regra de atribuição

O inventário confirmado no código-base contém **53 tabelas existentes**: 51 declarações em 22 arquivos `models.py`/`*_models.py`, mais duas classes ORM declaradas nos serviços de interrupção e cancelamento de viagens.

| Classe | Quantidade | Tratamento |
|---|---:|---|
| ORG | 13 | `organization_id = LEGACY_ORGANIZATION_ID` |
| HERDADO | 27 | Mesmo valor legado materializado na própria linha; validar relação com o agregado pai |
| GLOBAL | 8 | Não adicionar `organization_id` |
| CONTEXTO | 1 | `auth_sessions.active_organization_id`, criado pela 0036 |
| MISTO | 3 | Aplicar regra específica por linha/categoria |
| LEGADO | 1 | Copiar dados para `organizations`, manter origem durante a transição |
| **Total** | **53** | |

### 2.1 ORG — 13 tabelas

`access_profiles`, `customers`, `products`, `drivers`, `trucks`, `orders`, `load_plans`, `load_distributions`, `optimization_requests`, `trips`, `status_history`, `external_commands`, `registration_imports`.

### 2.2 HERDADO — 27 tabelas

`access_profile_permissions`, `customer_addresses`, `driver_documents`, `driver_document_policies`, `truck_maintenances`, `truck_documents`, `truck_document_policies`, `order_items`, `load_plan_orders`, `load_plan_items`, `load_distribution_orders`, `load_distribution_parts`, `load_distribution_volumes`, `loading_sessions`, `loading_session_items`, `deliveries`, `delivery_exceptions`, `trip_interruption_events`, `trip_cancellations`, `occurrences`, `delivery_evidences`, `operational_attachments`, `operational_notifications`, `notification_recipients`, `outbox_events`, `outbox_attempts`, `outbox_retry_commands`.

### 2.3 GLOBAL — 8 tabelas

`users`, `auth_login_throttles`, `auth_password_resets`, `auth_factors`, `auth_challenges`, `auth_recovery_codes`, `auth_trusted_devices`, `access_permissions`.

### 2.4 CONTEXTO — 1 tabela

`auth_sessions`. A migration 0036 adiciona `active_organization_id`, preenche as sessões existentes pela membership legada e exige contexto não nulo com FK composta para `organization_memberships(organization_id, user_id)`.

### 2.5 MISTO — 3 tabelas

- `driver_document_types`: CNH nativa global; tipos customizados da organização legada.
- `notification_preferences`: `SECURITY` global; `TRIPS` e `OCCURRENCES` da organização legada.
- `audit_events`: separar eventos de identidade/plataforma dos eventos organizacionais e das preferências.

### 2.6 LEGADO — 1 tabela

`company_profiles`. Não recebe `organization_id`. Seus seis campos são migrados para `organizations`; a tabela antiga permanece disponível até a migração dos consumidores e a reconciliação final.

**Regra de atribuição:** como a base de origem representa uma única instalação/empresa, o backfill das 40 tabelas ORG/HERDADO usa o UUID fixo da organização legada. Não inferir tenant por `actor_id`, `user_id`, CNPJ, placa, header, payload ou consulta isolada ao pai. O valor constante não dispensa a validação de órfãos e de relações entre agregados.

## 3. Fase 0 — baseline somente leitura

Executar em uma cópia isolada da base, antes da migration 0036. Guardar o resultado com data, SHA do dump e versão PostgreSQL.

### 3.1 Contagem exata das 53 tabelas

O bloco abaixo produz uma linha por tabela, sem usar estimativas de `reltuples`:

```sql
CREATE TEMP TABLE tenancy_preflight_counts (
    table_name text PRIMARY KEY,
    row_count bigint NOT NULL
) ON COMMIT PRESERVE ROWS;

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'users', 'auth_login_throttles', 'auth_sessions',
        'auth_password_resets', 'auth_factors', 'auth_challenges',
        'auth_recovery_codes', 'auth_trusted_devices',
        'access_permissions', 'access_profiles', 'access_profile_permissions',
        'company_profiles', 'customers', 'customer_addresses', 'products',
        'drivers', 'driver_document_types', 'driver_documents',
        'driver_document_policies', 'trucks', 'truck_maintenances',
        'truck_documents', 'truck_document_policies', 'orders', 'order_items',
        'load_plans', 'load_plan_orders', 'load_plan_items', 'load_distributions',
        'load_distribution_orders', 'load_distribution_parts',
        'load_distribution_volumes', 'optimization_requests', 'loading_sessions',
        'loading_session_items', 'trips', 'deliveries', 'delivery_exceptions',
        'trip_interruption_events', 'trip_cancellations', 'occurrences',
        'delivery_evidences', 'status_history', 'audit_events',
        'operational_attachments', 'operational_notifications',
        'notification_recipients', 'notification_preferences', 'outbox_events',
        'outbox_attempts', 'outbox_retry_commands', 'external_commands',
        'registration_imports'
    ]
    LOOP
        EXECUTE format(
            'INSERT INTO pg_temp.tenancy_preflight_counts(table_name, row_count)
             SELECT %L, count(*) FROM public.%I',
            table_name,
            table_name
        );
    END LOOP;
END $$;

SELECT table_name, row_count
FROM tenancy_preflight_counts
ORDER BY table_name;
```

Somar os resultados e guardar a contagem por tabela como baseline. Depois da 0036, repetir a contagem das 53 e contar separadamente as quatro tabelas novas: `organizations`, `organization_memberships`, `organization_invitations` e `platform_owner_grants`. A alteração de `auth_sessions` é coluna, não uma tabela adicional.

**Não preencher contagens estimadas no documento.** Os números reais só entram no relatório após execução no clone PostgreSQL 16.

### 3.2 Empresa singleton e CNPJ

```sql
SELECT id, legal_name, display_name, cnpj, phone, email, logo_reference
FROM company_profiles
ORDER BY id;

SELECT count(*) AS invalid_cnpj_rows
FROM company_profiles
WHERE cnpj IS NOT NULL
  AND cnpj !~ '^[0-9]{14}$';
```

Critérios:

- A linha esperada usa `PROFILE_ID = 00000000-0000-0000-0000-000000000091`.
- Se não houver linha, a fallback `Empresa legada` da 0036 exige decisão explícita e registro no relatório.
- Qualquer CNPJ não numérico ou diferente de 14 dígitos bloqueia o backfill até correção aprovada.
- Se o UUID fixo da organização já existir em um banco parcialmente migrado, comparar todos os campos; não aceitar `ON CONFLICT DO NOTHING` como prova de equivalência.
- A constraint de `organizations.cnpj` deve validar também os 14 dígitos, não apenas o comprimento.

### 3.3 Consistência dos usuários para a membership legada

A 0036 copia `users.role`, `custom_profile_id` e `driver_id` para a membership. Validar as mesmas regras das CHECKs antes de aplicar a migration:

```sql
SELECT id, role, custom_profile_id, driver_id
FROM users
WHERE role NOT IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER', 'CUSTOM')
   OR ((role = 'CUSTOM') IS DISTINCT FROM (custom_profile_id IS NOT NULL))
   OR (driver_id IS NOT NULL AND role <> 'DRIVER')
ORDER BY id;
```

O resultado precisa ser vazio. Verificar também que cada `custom_profile_id` existe em `access_profiles`, cada `driver_id` existe em `drivers`, e que os valores atuais não serão perdidos ao criar a membership. Não alterar os campos globais de compatibilidade nesta fase.

### 3.4 Sessões e FKs existentes

- Contar sessões por estado e usuário.
- Confirmar que toda sessão referencia um usuário existente.
- Listar FKs não validadas em `pg_constraint`; qualquer FK atual não validada precisa de explicação antes de avançar.
- Conferir se há uma linha preexistente com `LEGACY_ORGANIZATION_ID`.
- Não apagar sessões expiradas para fazer a migration passar: elas também precisam de contexto ou de uma decisão de expurgo independente e auditada.

## 4. Fase 1 — aplicar e validar a fundação #449 em clone

Somente depois de aprovar o baseline:

1. Aplicar a migration 0036 em PostgreSQL 16 isolado.
2. Confirmar que existe exatamente uma organização com `id = LEGACY_ORGANIZATION_ID` e `is_legacy = true`.
3. Confirmar que a contagem de `organization_memberships` corresponde à contagem de `users`, pois a 0036 cria uma membership legada para cada identidade existente.
4. Confirmar que cada par `(organization_id, user_id)` é único e que não há membership fora da organização legada.
5. Confirmar que nenhuma sessão ficou com `active_organization_id IS NULL`.
6. Confirmar que cada sessão aponta para a membership ativa do mesmo usuário e da organização legada.
7. Executar `alembic check` e os testes de migração/fundação em PostgreSQL 16.
8. Não conceder `platform_owner_grants` automaticamente; o grant permanece vazio até decisão separada.

Se qualquer contagem divergir, interromper e reconciliar antes de adicionar `organization_id` às tabelas operacionais.

## 5. Fase 2 — expandir o schema sem quebrar compatibilidade

A implementação futura deve seguir expand/contract:

1. Adicionar `organization_id` inicialmente nullable às 40 tabelas ORG/HERDADO.
2. Adicionar chaves únicas de referência `(organization_id, id)` nos pais que serão alvo de FKs compostas.
3. Adicionar FKs compostas novas sem remover as FKs antigas.
4. Criar índices organizacionais e índices de idempotência; manter as unicidades antigas enquanto a aplicação ainda depender delas.
5. Adicionar as colunas e constraints específicas das tabelas MISTO.
6. Acrescentar `phone`, `email` e `logo_reference` a `organizations`; a 0036 já copia `legal_name`, `display_name` e `cnpj`.
7. Só validar e tornar `organization_id` NOT NULL depois do backfill e da reconciliação.

Para tabelas grandes, avaliar backfill em lotes por PK, com checkpoint e limite de duração. Para tabelas pequenas, uma transação única pode ser mais simples. O tamanho real será decidido pelas contagens do clone, não por suposição.

## 6. Fase 3 — backfill determinístico

### 6.1 Tabelas ORG/HERDADO

Para cada tabela do inventário, preencher somente linhas nulas:

```sql
UPDATE public.nome_da_tabela
SET organization_id = '00000000-0000-4000-8000-000000000301'::uuid
WHERE organization_id IS NULL;
```

Executar em lotes quando necessário e registrar por tabela:

- quantidade elegível antes;
- quantidade atualizada;
- quantidade ainda nula;
- quantidade com organização diferente da legada;
- duração, lote e checkpoint.

Não usar `UPDATE ... FROM parent` para inferir o tenant. A base de origem é single-tenant; a atribuição é constante e a relação pai/filho será provada separadamente pelas FKs compostas e pelos checks de domínio.

### 6.2 `driver_document_types`

- Preservar `CNH_TYPE_ID = 00000000-0000-4000-8000-000000000102` e código `CNH` como catálogo global (`organization_id IS NULL`).
- A primeira etapa possui apenas essa linha global; qualquer divergência entre UUID, código e nome deve bloquear a migração.
- Atribuir `LEGACY_ORGANIZATION_ID` a todos os tipos customizados existentes.
- Reservar o código `CNH`; um tipo customizado não pode sobrescrever ou sombrear o tipo global.
- Criar unicidade parcial global por `code` e organizacional por `(organization_id, code)`.
- Em `driver_documents` e `driver_document_policies`, validar no banco que o tipo é global ou pertence à mesma organização do motorista. A FK composta do motorista não substitui essa verificação do catálogo misto.

### 6.3 `notification_preferences`

- `SECURITY`: manter global, `organization_id IS NULL` e `enabled = true`.
- `TRIPS` e `OCCURRENCES`: associar à organização legada e exigir membership correspondente.
- A PK atual `(user_id, category)` não permite várias empresas; substituir por identificador estável e índices UNIQUE parciais: `(user_id, category)` para SECURITY e `(organization_id, user_id, category)` para preferências operacionais.
- CHECK deve impedir categoria/escopo incompatíveis.
- Se não existir linha, preservar o comportamento atual `enabled = true`; não criar linhas desnecessárias.
- GET/PUT futuro deriva organização da sessão ativa, nunca de body/header.

### 6.4 `audit_events`

O schema atual usa `entity_type`, `entity_id`, `actor_id` e `changed_fields VARCHAR(512)`. O serviço serializa `changed_fields` com vírgulas; portanto, o backfill deve tratar a string como lista delimitada, validar cada nome e rejeitar valores desconhecidos.

Mapeamento:

| Evento atual | Destino |
|---|---|
| `entity_type=USER`, campos `name/email/active/password` | `USER_IDENTITY`, escopo PLATFORM |
| `USER_CREATED`, campos `role/driver_id` | `MEMBERSHIP_CREATED`, entidade membership da organização legada |
| `USER_UPDATED`, campos `role/custom_profile_id/driver_id` | `MEMBERSHIP_UPDATED`, entidade membership da organização legada |
| `notification_preferences.SECURITY` | `NOTIFICATION_PREFERENCE`, escopo PLATFORM |
| `notification_preferences.TRIPS/OCCURRENCES` | `NOTIFICATION_PREFERENCE`, organização legada |
| `COMPANY_PROFILE_*` / `COMPANY_PROFILE` | `ORGANIZATION`, UUID da organização legada |
| `DRIVER_DOCUMENT_TYPE` | PLATFORM para CNH global; organização legada para tipo customizado |
| Eventos de clientes, produtos, frota, documentos, anexos, perfis, importações e outbox | Entidade organizacional correspondente |

Regras adicionais:

- `USER_CREATED` atual registra `active`, `driver_id`, `email`, `name` e `role`, mas não inclui `custom_profile_id` em `changed_fields`. Para o evento de membership, obter o perfil do snapshot da membership criada pela 0036; não inventar o campo no histórico.
- Um `USER_UPDATED` pode conter campos globais, de membership e de preferências. Dividir em até três eventos, mantendo o mesmo instante e ator.
- Para preservar a origem, adicionar `source_event_id`: eventos originais reclassificados recebem seu próprio UUID; cópias geradas pela divisão recebem novo UUID e apontam para o mesmo `source_event_id`.
- `actor_id` continua sendo identidade global. Para eventos ORGANIZATION, comprovar membership do ator na organização legada; para PLATFORM, não exigir membership.
- `COMPANY_PROFILE` precisa ser remapeado para `ORGANIZATION`, pois o ID singleton antigo não é o ID da nova organização.
- Atualizar CHECKs de `event_type` e `entity_type` antes de inserir os novos tipos `USER_IDENTITY`, `MEMBERSHIP`, `NOTIFICATION_PREFERENCE` e `ORGANIZATION`.
- Qualquer evento, campo, entidade ou ator organizacional sem mapeamento inequívoco vai para quarentena e bloqueia o cutover.
- Depois da migração, tornar a trilha append-only também no banco, protegendo contra UPDATE/DELETE; ausência de endpoint não é garantia de imutabilidade.

### 6.5 `company_profiles`

- Copiar `phone`, `email` e `logo_reference` para as novas colunas de `organizations`.
- Reconciliar também `legal_name`, `display_name` e `cnpj`, que a 0036 já copia.
- Comparar os seis valores normalizados entre origem e destino.
- Validar que o objeto de logo existe no storage e que seu caminho não é compartilhado com outro tenant; não mover ou apagar o arquivo nesta etapa.
- Manter `company_profiles` e seus consumidores até uma etapa de descontinuação separada.

## 7. Fase 4 — órfãos, integridade e reconciliação

### 7.1 Órfãos polimórficos de `status_history`

A tabela não possui FK convencional para todos os tipos. Antes e depois do backfill, cada `entity_type/entity_id` precisa apontar para uma linha real:

```sql
SELECT h.id, h.entity_type, h.entity_id
FROM status_history h
WHERE CASE h.entity_type
    WHEN 'ORDER' THEN EXISTS (SELECT 1 FROM orders x WHERE x.id = h.entity_id)
    WHEN 'LOAD_PLAN' THEN EXISTS (SELECT 1 FROM load_plans x WHERE x.id = h.entity_id)
    WHEN 'TRIP' THEN EXISTS (SELECT 1 FROM trips x WHERE x.id = h.entity_id)
    WHEN 'DELIVERY' THEN EXISTS (SELECT 1 FROM deliveries x WHERE x.id = h.entity_id)
    WHEN 'LOAD_DISTRIBUTION' THEN EXISTS (
        SELECT 1 FROM load_distributions x WHERE x.id = h.entity_id
    )
    WHEN 'LOAD_DISTRIBUTION_PART' THEN EXISTS (
        SELECT 1 FROM load_distribution_parts x WHERE x.id = h.entity_id
    )
    ELSE false
END IS NOT TRUE;
```

O resultado deve ser vazio. Depois de adicionar `organization_id`, validar também que a linha alvo tem o mesmo valor.

### 7.2 Órfãos polimórficos de `audit_events`

Antes da transformação, validar cada combinação atual:

- USER → `users`
- CUSTOMER → `customers`
- PRODUCT → `products`
- TRUCK → `trucks`
- DRIVER → `drivers`
- CUSTOMER_ADDRESS → `customer_addresses`
- TRUCK_MAINTENANCE → `truck_maintenances`
- TRUCK_DOCUMENT → `truck_documents`
- TRUCK_DOCUMENT_POLICY → `truck_document_policies`
- DRIVER_DOCUMENT → `driver_documents`
- DRIVER_DOCUMENT_POLICY → `driver_document_policies`
- DRIVER_DOCUMENT_TYPE → `driver_document_types`
- ATTACHMENT → `operational_attachments`
- REGISTRATION_IMPORT → `registration_imports`
- COMPANY_PROFILE → `company_profiles`
- ACCESS_PROFILE → `access_profiles`
- OUTBOX_EVENT → `outbox_events`

Qualquer `entity_type` fora da lista ou `entity_id` sem destino deve ser exportado para quarentena. Após o remapeamento, validar novamente com os tipos e IDs de destino.

### 7.3 Integridade de relações e atores

Verificar, no mínimo:

- `customer_addresses.customer_id → customers`.
- `orders.customer_id/address_id → customers/customer_addresses`.
- `order_items.order_id/product_id → orders/products`.
- `load_plan_orders` e `load_plan_items` → plano, pedido, item e produto do mesmo tenant.
- Distribuições, partes e volumes → distribuição, plano, pedido e item do mesmo tenant.
- `trips` → plano e motorista da mesma organização.
- `deliveries` → viagem, pedido e parte de distribuição compatíveis.
- Exceções, interrupções e cancelamentos → viagem/entrega correspondente.
- Ocorrências e evidências → viagem, entrega e histórico correspondentes.
- Anexos → exatamente um pai válido entre pedido, viagem, entrega e ocorrência.
- Notificações → viagem, origem (histórico/ocorrência) e motorista destinatário compatíveis.
- Recibos de notificação → usuário com membership na organização da notificação.
- Outbox e tentativas → notificação/evento de origem; retries → evento e ator autorizados.
- `optimization_requests`, `external_commands` e `registration_imports` → usuário/membership e resultado no mesmo tenant.
- `status_history.changed_by`, atores de exceções, cancelamentos, interrupções, evidências e anexos → membership contextual quando o evento for organizacional.

A implementação deve criar unicidade `(organization_id, id)` nos pais e FKs compostas nas relações. Para atores organizacionais, preferir FK composta `(organization_id, actor_user_id)` para `organization_memberships(organization_id, user_id)`; eventos PLATFORM continuam usando a FK global de identidade.

### 7.4 Unicidades e idempotência

Verificar duplicidades antes de criar índices:

- `customers(document)`, `products(code)`, `drivers(document)`, `drivers(license_number)`, `trucks(plate)`, `access_profiles(name_key)`.
- `external_commands(integration_id, event_hash)`.
- `optimization_requests(user_id, request_key)`.
- `registration_imports(recorded_by, event_id)`.
- `operational_attachments(recorded_by, event_id)` e `delivery_evidences(recorded_by, event_id)`.
- `trip_interruption_events(idempotency_key)` e `trip_cancellations(trip_id/idempotency_key)`.
- Notificações e outbox: chaves de origem, `notification_id`, `idempotency_key` e geração de tentativa.

Depois da expansão, os índices de negócio devem incluir `organization_id` quando o valor for tenant-owned. Preservar unicidade global de email/identidade, permissões globais e códigos reservados do catálogo de plataforma.

### 7.5 Relatório de reconciliação obrigatório

Para cada tabela, registrar:

| Campo | Critério |
|---|---|
| `count_before` | Contagem exata antes da migration |
| `count_after` | Contagem exata após backfill |
| `delta` | Zero, exceto linhas novas de auditoria criadas pela divisão documentada |
| `organization_id_null` | Zero em ORG/HERDADO |
| `unexpected_org_count` | Zero antes da liberação multiempresa |
| `orphan_count` | Zero |
| `cross_tenant_fk_count` | Zero |
| `unique_conflict_count` | Zero |
| `quarantine_count` | Zero para liberar cutover |
| `checksum/sample_ids` | Preservação de IDs e amostras determinísticas |

As linhas extras de `audit_events` geradas pela divisão precisam ser explicadas por `source_event_id`; não são perda nem duplicação silenciosa. Todas as demais tabelas devem manter a contagem e os UUIDs originais.

## 8. Fase 5 — validar constraints e preparar cutover

1. Criar índices únicos compostos e chaves de referência `(organization_id, id)`.
2. Adicionar FKs compostas como `NOT VALID` quando suportado, sem remover as FKs simples.
3. Executar checks de órfãos e relações cross-tenant.
4. Executar `VALIDATE CONSTRAINT` em cada FK nova.
5. Confirmar zero `organization_id IS NULL` em ORG/HERDADO.
6. Aplicar `NOT NULL` somente depois de todos os relatórios aprovados.
7. Manter constraints globais antigas até que todos os repositórios e serviços usem o escopo organizacional.
8. Atualizar repositories, services, rotas, workers, relatórios, anexos, busca, notificações, outbox, importações e Loxi para exigir contexto.
9. Executar testes negativos com duas organizações no PostgreSQL 16, incluindo UUID conhecido, leitura, escrita, FK cruzada, arquivo, relatório, cache, worker e retry.
10. Manter a feature flag desligada até revisão de segurança independente.

RLS não faz parte deste backfill. Se adotada posteriormente, deve ser provada com a role real de runtime, pool, transações, `SET LOCAL`, rollback e workers.

## 9. Estratégia de rollback

### Antes de qualquer dado de uma segunda organização

- Tirar snapshot/backup consistente e testar restauração antes de cada fase destrutiva.
- Manter `company_profiles`, campos de compatibilidade em `users`, FKs antigas e unicidades antigas durante a transição.
- Se uma fase falhar, interromper workers/escritas e reverter a transação ou migration corrente.
- A migration de backfill só pode remover colunas/índices novos se todas as linhas estiverem exclusivamente na organização legada e as constraints antigas continuarem íntegras.
- Não apagar nem reescrever histórico para fazer downgrade passar.

### Depois de existir dado em outra organização

- Proibir downgrade que reatribua tudo à organização legada.
- A reversão exige interromper escrita, snapshot restaurável e plano explícito de reconciliação; não é seguro colapsar tenants automaticamente.
- A migration deve falhar de forma explícita se encontrar `organization_id <> LEGACY_ORGANIZATION_ID`, memberships adicionais, convites aceitos ou referências novas que seriam perdidas.
- A 0036 já protege parte do downgrade contra histórico de convites, grants e memberships alteradas; preservar e ampliar essa postura fail-closed.

## 10. Runbook de execução futura

- [ ] PR #454 da matriz revisada e integrada.
- [ ] PR #449 da fundação revisada e integrada.
- [ ] Backup/snapshot do clone PostgreSQL 16 criado e restauração testada.
- [ ] Baseline de contagens das 53 tabelas arquivado.
- [ ] Pré-validação de `company_profiles`, usuários, perfis, motoristas e sessões aprovada.
- [ ] Workers, outbox e importações pausados durante a janela de backfill.
- [ ] Migration expand aplicada no clone.
- [ ] Backfill executado com checkpoint e log por tabela.
- [ ] Casos MISTO/LEGADO reconciliados.
- [ ] Órfãos, unicidades, FKs compostas e atores validados.
- [ ] Relatório before/after assinado e sem quarentena.
- [ ] Testes de rollback e restore aprovados.
- [ ] Testes negativos com duas organizações aprovados.
- [ ] Revisão independente de segurança concluída.
- [ ] Feature flag ainda desligada até autorização explícita.

## 11. Situação desta entrega

Este plano foi preparado por inspeção do código, models, services, ADR-049 e migration 0036. **Nenhuma contagem de produção foi consultada**, nenhum banco remoto foi acessado e nenhum backfill/migration de scoping foi executado.

O próximo artefato operacional, depois da aprovação da matriz e deste plano, será um conjunto de migrations pequenas por grupo de tabelas, acompanhado de testes PostgreSQL 16. A execução começa em clone isolado e só avança após reconciliação.
