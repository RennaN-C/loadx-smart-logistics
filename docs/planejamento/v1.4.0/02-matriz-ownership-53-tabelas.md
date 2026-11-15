# Matriz de ownership multiempresa — 53 tabelas existentes

- **Data:** 15/11/2026
- **Base analisada:** branch **desenvolvimento**, commit **af70acdb**
- **Fundação de organizações:** PR [#449](https://github.com/RennaN-C/loadx-smart-logistics/pull/449), ainda aberta e sem merge.
- **Referências:** ADR-049, Issue [#441](https://github.com/RennaN-C/loadx-smart-logistics/issues/441) e auditoria técnica incluída na PR #449.

## 1. Objetivo e limite

Esta matriz fixa a decisão de ownership das **53 tabelas ORM já existentes** antes de adicionar escopo organizacional aos dados operacionais. A conferência inclui as tabelas declaradas em arquivos de modelos e as duas tabelas declaradas diretamente nos serviços de interrupção e cancelamento de viagem.

As quatro tabelas novas da fundação (#449) não entram na contagem das 53: **organizations**, **organization_memberships**, **organization_invitations** e **platform_owner_grants**. A migration 0036 também acrescenta **active_organization_id** a **auth_sessions**, que já faz parte das 53. Com a fundação aplicada, a metadata passa a conter **57 tabelas**.

**Esta matriz não habilita multiempresa.** Na base atual, os dados logísticos ainda são single-tenant. A sessão contextual da PR #449 também não prova isolamento dos repositórios. Nenhuma segunda organização poderá operar até a implementação, os testes negativos e a revisão de segurança das fases seguintes.

## 2. Classes de ownership

| Classe | Significado | Regra de implementação |
|---|---|---|
| **ORG** | Registro pertence diretamente a uma organização | Adicionar **organization_id NOT NULL**, índice e chave única composta **(organization_id, id)** para FKs compostas |
| **HERDADO** | Registro pertence ao mesmo tenant do agregado pai | Também materializar **organization_id NOT NULL**; validar pai e filho por FK composta, não depender apenas de JOIN |
| **GLOBAL** | Identidade, segurança global ou catálogo compartilhado | Não adicionar **organization_id**; operações em nome de uma empresa exigem membership validada |
| **CONTEXTO** | Registro global de sessão que carrega a organização ativa | Validar sessão, usuário, membership e estado da organização em cada request |
| **MISTO** | Registro, catálogo ou preferência pode ter escopo global/plataforma ou pertencer a uma organização | Representar o escopo explicitamente; organization_id nulo somente para registros globais e obrigatório para registros organizacionais; impor CHECKs, unicidades e FKs que impeçam uso cruzado |
| **LEGADO** | Estrutura singleton da instalação atual, sem ownership multiempresa válido | Migrar os campos para o cadastro da organização legada e retirar a dependência do singleton |

**Regra geral:** em tabelas ORG e HERDADO, o **organization_id** deve estar gravado na própria linha. Não inferir tenant pelo **actor_id**, **user_id**, placa, CNPJ, ID de pai consultado separadamente, header ou payload do cliente. IDs UUID globais não substituem FKs compostas.

## 3. Matriz das 53 tabelas

| # | Tabela | Classe | Ownership e tratamento obrigatório |
|---:|---|---|---|
| 1 | **users** | GLOBAL | Identidade global: e-mail e credenciais continuam únicos na plataforma. **role**, **custom_profile_id** e **driver_id** são campos legados de autorização; a fonte de verdade passa a ser **organization_memberships**. Mantê-los apenas durante a compatibilidade e removê-los da decisão RBAC após migração validada. |
| 2 | **auth_login_throttles** | GLOBAL | Proteção contra abuso por conta/IP. Manter global para que trocar de organização não permita contornar bloqueio ou orçamento de tentativas. |
| 3 | **auth_sessions** | CONTEXTO | Sessão pertence à identidade e carrega uma organização ativa. A PR #449 adiciona **active_organization_id** e FK composta com membership. Validar organização ativa e membership em cada resolução; nunca aceitar seleção por header ou body. |
| 4 | **auth_password_resets** | GLOBAL | Recuperação de credencial da identidade global. Token e consumo não pertencem a uma organização específica. |
| 5 | **auth_factors** | GLOBAL | MFA/TOTP é fator da identidade global. Política de MFA não pode depender de um **User.role** global depois da contextualização dos papéis. |
| 6 | **auth_challenges** | GLOBAL | Desafio de autenticação da identidade. Revisar o campo **role** armazenado como snapshot: se a exigência de MFA variar por papel organizacional, registrar o contexto/decisão de política sem transformar o desafio em autorização de tenant. |
| 7 | **auth_recovery_codes** | GLOBAL | Códigos de recuperação pertencem à identidade global e são consumidos uma única vez, independentemente da organização ativa. |
| 8 | **auth_trusted_devices** | GLOBAL | Dispositivo confiável pertence à identidade global. Revogação e vínculo de segurança devem valer em todas as organizações. |
| 9 | **access_permissions** | GLOBAL | Catálogo estável de permissões do produto. Não duplicar por organização; concessões são associadas a perfis organizacionais. |
| 10 | **access_profiles** | ORG | Perfil customizado pertence a uma empresa. Adicionar **organization_id**; trocar unicidade global de **name_key** por unicidade **(organization_id, name_key)**. |
| 11 | **access_profile_permissions** | HERDADO | Associação herda a organização do perfil. Incluir **organization_id** ou garantir FK composta que prove o perfil no mesmo tenant; **permission_code** continua apontando para o catálogo global. |
| 12 | **company_profiles** | LEGADO | Tabela singleton representa a instalação atual, não uma empresa SaaS. Migrar **legal_name**, **display_name**, **cnpj**, **phone**, **email** e **logo_reference** para **organizations**, acrescentando os três últimos campos ao cadastro organizacional. A migration 0036 copia apenas nome empresarial, nome de exibição e CNPJ: preservar a tabela de origem até migrar telefone/e-mail/logo, reconciliar os seis campos e migrar todos os consumidores; só então descontinuar o singleton. |
| 13 | **customers** | ORG | Cadastro de cliente pertence à organização. Documento deixa de ser globalmente único e passa a ser único por organização, conforme regra de negócio. |
| 14 | **customer_addresses** | HERDADO | Endereço pertence ao cliente. FK composta **(organization_id, customer_id)** e unicidade/índice de endereço primário no escopo do cliente e tenant. |
| 15 | **products** | ORG | Catálogo de produtos é da empresa. **code** passa a ser único por organização; snapshots históricos continuam preservados em itens de planejamento. |
| 16 | **drivers** | ORG | Cadastro de motorista pertence à empresa. Documento e número de CNH deixam de ser chaves globais e passam a ser únicos por organização, conforme validação de negócio. Membership que representa motorista deve referenciar o driver da mesma organização. |
| 17 | **driver_document_types** | MISTO | O tipo nativo CNH (`CNH_TYPE_ID`) permanece global e reservado. Tipos customizados criados por `DriverManager` pertencem à organização ativa. Preservar o UUID/código da CNH e migrar todos os tipos customizados existentes para a organização legada. A listagem deve combinar catálogo global e tipos da organização ativa; o POST deriva a organização da sessão, nunca do cliente. Manter unicidade global para códigos reservados e `(organization_id, code)` para tipos customizados. `driver_documents` e `driver_document_policies` só podem usar tipo global ou tipo customizado da mesma organização do motorista; essa relação exige integridade contextual no banco (FKs adequadas ou trigger), não apenas validação de aplicação. |
| 18 | **driver_documents** | HERDADO | Documento pertence ao motorista. FK composta para o motorista da mesma organização; o tipo documental pode ser o tipo global reservado ou um tipo customizado da mesma organização. A integridade do par organização/tipo deve ser garantida no banco, não apenas na aplicação. |
| 19 | **driver_document_policies** | HERDADO | Política documental pertence ao motorista/empresa. FK composta para driver; o tipo referenciado pode ser global reservado ou customizado da mesma organização, com integridade contextual garantida no banco. |
| 20 | **trucks** | ORG | Frota pertence à empresa. Placa passa a ser única por organização, não globalmente. |
| 21 | **truck_maintenances** | HERDADO | Manutenção pertence ao caminhão. FK composta **(organization_id, truck_id)** e consultas sempre no contexto da empresa. |
| 22 | **truck_documents** | HERDADO | Documento pertence ao caminhão. FK composta para o caminhão; validar também a referência do arquivo e o caminho no storage dentro da organização. |
| 23 | **truck_document_policies** | HERDADO | Política documental pertence ao caminhão/empresa. FK composta para o caminhão; unicidade de tipo dentro do caminhão e tenant. |
| 24 | **orders** | ORG | Pedido pertence à empresa. Cliente e endereço precisam pertencer à mesma organização; criar FKs compostas para ambos. |
| 25 | **order_items** | HERDADO | Item pertence ao pedido e referencia produto do mesmo tenant. FKs compostas para **(organization_id, order_id)** e **(organization_id, product_id)**. |
| 26 | **load_plans** | ORG | Planejamento pertence à empresa. Caminhão e plano de origem de recálculo precisam ser do mesmo tenant; preservar snapshots e histórico. |
| 27 | **load_plan_orders** | HERDADO | Junção entre planejamento e pedido. FKs compostas devem impedir que plano e pedido de empresas diferentes sejam associados. |
| 28 | **load_plan_items** | HERDADO | Item planejado pertence ao plano e referencia pedido, item do pedido e produto do mesmo tenant. Preservar as FKs de proveniência já existentes, acrescentando organization_id a todas as relações. |
| 29 | **load_distributions** | ORG | Distribuição multi-caminhão pertence à empresa. **created_by** é identidade global, mas a ação deve exigir membership autorizada na organização da distribuição. |
| 30 | **load_distribution_orders** | HERDADO | Junção entre distribuição e pedido. FKs compostas garantem mesmo tenant; unicidade de pedido ativo fica no escopo organizacional. |
| 31 | **load_distribution_parts** | HERDADO | Parte pertence à distribuição e ao plano de carga. Ambos precisam compartilhar organization_id; manter integridade de status e histórico. |
| 32 | **load_distribution_volumes** | HERDADO | Volume pertence à distribuição/parte e deriva de order item, pedido e produto. Todas as FKs compostas devem comprovar o mesmo tenant, preservando a identidade do volume. |
| 33 | **optimization_requests** | ORG | Idempotência do otimizador precisa ser organizacional: chave recomendada **(organization_id, user_id, request_key)**. Distribuição resultante e usuário solicitante devem estar no contexto validado. |
| 34 | **loading_sessions** | HERDADO | Sessão de carregamento pertence ao plano de carga. FK composta para o plano; nunca permitir sessão sobre plano de outra organização. |
| 35 | **loading_session_items** | HERDADO | Item de conferência pertence à sessão e ao item do plano. FKs compostas devem garantir que ambos vêm do mesmo plano/tenant. |
| 36 | **trips** | ORG | Viagem pertence à empresa. Plano e motorista precisam pertencer à mesma organização; **load_plan_id** continua único no escopo correto. |
| 37 | **deliveries** | HERDADO | Entrega pertence à viagem e ao pedido; **distribution_part_id**, quando presente, também deve ser do mesmo tenant. Revisar índices únicos parciais com organization_id. |
| 38 | **delivery_exceptions** | HERDADO | Exceção pertence à entrega e viagem; ambas devem pertencer à mesma organização. **actor_id** exige membership válida no tenant. |
| 39 | **trip_interruption_events** | HERDADO | Evento de interrupção/retomada pertence à viagem. Incluir organization_id, FK composta para trip e idempotência por organização; a tabela é declarada em **interruption_service.py**, não em **models.py**. |
| 40 | **trip_cancellations** | HERDADO | Cancelamento pertence à viagem. Incluir organization_id, FK composta para trip e chave idempotente no escopo da organização; a tabela é declarada em **cancellation_service.py**. |
| 41 | **occurrences** | HERDADO | Ocorrência pertence à viagem e, quando aplicável, à entrega da mesma organização. Fotos/URLs precisam seguir o mesmo escopo de arquivo. |
| 42 | **delivery_evidences** | HERDADO | Evidência pertence à entrega e ao evento de histórico correspondente. Validar ambos no mesmo tenant e exigir membership do autor/revogador. |
| 43 | **status_history** | ORG | Histórico polimórfico é tenant-owned. Adicionar organization_id obrigatório e validar **entity_type/entity_id** contra o recurso real do mesmo tenant; não confiar apenas no UUID ou em uma FK inexistente. |
| 44 | **audit_events** | MISTO | A tabela reúne eventos de identidade, memberships, preferências, perfis, cadastros e operações organizacionais. Adicionar escopo explícito (`PLATFORM`/`ORGANIZATION`) e `organization_id` obrigatório no segundo caso; impor CHECK de coerência e validar o alvo por tipo. Após a migração de RBAC, distinguir `USER_IDENTITY` (global), `MEMBERSHIP` (organizacional), `NOTIFICATION_PREFERENCE` (global ou organizacional conforme categoria) e `ACCESS_PROFILE` (organizacional), atualizando a whitelist de `entity_type`. **Backfill:** classificar por `entity_type` e `changed_fields`, nunca por `actor_id`: eventos de entidades operacionais, `COMPANY_PROFILE`, `ACCESS_PROFILE`, `DRIVER_DOCUMENT_TYPE` customizado, `ATTACHMENT`, `REGISTRATION_IMPORT` e `OUTBOX_EVENT` pertencem à organização legada. Em eventos atuais `USER_CREATED`/`USER_UPDATED`, `name`, `email`, `active`, senha, MFA e dispositivos confiáveis permanecem `PLATFORM`; `role`, `custom_profile_id` e `driver_id` viram eventos `MEMBERSHIP` da organização legada; `notification_preferences.SECURITY` permanece `PLATFORM`, enquanto `TRIPS`/`OCCURRENCES` viram eventos `NOTIFICATION_PREFERENCE` da organização legada. Resolver o membership/preference alvo pelo vínculo e escopo correspondentes. Quando um evento misturar campos globais e organizacionais, separar os grupos em registros com o mesmo instante/ator e referência ao ID original. Registros que não puderem ser classificados deterministicamente ficam em quarentena e bloqueiam a ativação até revisão. Manter append-only; se a auditoria da plataforma exigir retenção/ACL distinta, preferir tabela própria `platform_audit_events` em vez de ampliar permissões sobre auditoria operacional. |
| 45 | **operational_attachments** | HERDADO | Anexo aponta exatamente para um de order, trip, delivery ou occurrence. Adicionar organization_id e FKs/validação por recurso; downloads, revogação, URLs temporárias e object-storage keys precisam validar o tenant. |
| 46 | **operational_notifications** | HERDADO | Notificação operacional herda o tenant do trip/occurrence/status history e do motorista destinatário. Todas as origens e destinatários precisam ser da mesma organização. |
| 47 | **notification_recipients** | HERDADO | Recibo de leitura pertence à notificação e ao usuário/membership destinatário. FK composta deve provar que o usuário é membro da organização da notificação. |
| 48 | **notification_preferences** | MISTO | O código atual persiste por `user_id/category`, mas a ADR-049 e a auditoria da PR #449 definem escopos distintos: `SECURITY` permanece global e obrigatória; `TRIPS` e `OCCURRENCES` são preferências operacionais por organização/membership. Adicionar `organization_id` nullable: nulo somente para `SECURITY`, obrigatório para as outras categorias, com FK composta `(organization_id, user_id)` para membership. A PK atual `(user_id, category)` não suporta múltiplas organizações: usar identificador substituto e índices UNIQUE parciais para `(user_id, category)` global e `(organization_id, user_id, category)` organizacional, além de CHECK coerente entre categoria e escopo. GET/PUT deriva a organização da sessão ativa, nunca de body/header. Backfill: manter `SECURITY` global e associar as preferências `TRIPS`/`OCCURRENCES` existentes à organização legada. Sem linha mantém o padrão `enabled=true`. |
| 49 | **outbox_events** | HERDADO | Evento de entrega externa herda organization_id da notificação. Idempotency key e deduplicação devem incluir o tenant, preservando reprocessamento seguro. |
| 50 | **outbox_attempts** | HERDADO | Tentativa pertence ao outbox event. FK composta e índices de worker devem preservar o tenant em leases, retries e processamento assíncrono. |
| 51 | **outbox_retry_commands** | HERDADO | Comando de reprocessamento pertence ao evento e à organização dele. **actor_id** é identidade global, mas precisa de membership e permissão no tenant. |
| 52 | **external_commands** | ORG | Comando externo pertence à integração configurada pela organização. Incluir organization_id; unicidade **(organization_id, integration_id, event_hash)** e validar usuário/recursos de destino no mesmo tenant. |
| 53 | **registration_imports** | ORG | Importação pertence à empresa e ao usuário/membership que a executou. Incluir organization_id; escopar idempotência por organização e validar cada registro de customers/products/trucks/drivers criado a partir do JSON. |

## 4. Tabelas da fundação (#449), fora da contagem das 53

| Tabela | Escopo | Regra |
|---|---|---|
| **organizations** | Registro global do control plane | Cadastro e estado das organizações; não recebe organization_id de si mesma |
| **organization_memberships** | Vínculo organizacional | Relaciona identidade global a organização; role, perfil customizado e driver são contextuais |
| **organization_invitations** | Organização | Convite pertence à organização; token somente em hash, expirável, revogável e de uso único |
| **platform_owner_grants** | Plataforma/global | Concessão singleton do proprietário; não dá acesso automático aos dados operacionais dos tenants |

A migration 0036 já adiciona **active_organization_id** à tabela existente **auth_sessions**. Antes de liberar uma segunda organização, a fundação também precisa de integridade contextual nas referências internas: `organization_memberships(organization_id, custom_profile_id)` e `(organization_id, driver_id)` devem apontar para perfil e motorista da mesma organização; `organization_invitations(organization_id, custom_profile_id)` deve apontar para perfil da organização convidada. Os campos de ator do convite exigem validação de autorização contextual (membro ativo ou concessão de plataforma explicitamente permitida); FK simples para `users.id` prova apenas identidade, não autorização.

## 5. Decisões transversais obrigatórias

### 5.1 FKs compostas e integridade

Para cada tabela ORG/HERDADO:
1. Criar unicidade de referência **(organization_id, id)** nos agregados que serão pais de outras tabelas.
2. Trocar relações entre recursos para FKs compostas incluindo organization_id.
3. Em cada gravação, validar membership do ator na mesma organização; FK para **users.id** isolada prova identidade, não autorização.
4. Revisar triggers e constraints das migrations 0025–0034 para que transições e reconciliações não cruzem tenants.
5. Não relaxar **ON DELETE RESTRICT** nem remover histórico para facilitar backfill.

### 5.2 Unicidades que deixam de ser globais

Revisar explicitamente: **customers.document**, **products.code**, **drivers.document**, **drivers.license_number**, **trucks.plate** e **access_profiles.name_key**. Passam a ser únicas por organização, não na plataforma inteira.

Também revisar chaves de idempotência e deduplicação em **external_commands**, **optimization_requests**, **registration_imports**, **operational_attachments**, **delivery_evidences**, **trip_interruption_events**, **trip_cancellations**, notificações e outbox. Identificadores de evento não devem gerar colisão ou compartilhamento entre empresas.

### 5.3 Dados polimórficos, arquivos e processos assíncronos

- **status_history**, **audit_events** e **operational_attachments** não têm uma FK simples para todos os tipos de recurso. Exigem validação explícita do tipo, ID e organization_id na origem e na leitura.
- Storage, evidências, anexos, thumbnails e URLs temporárias devem carregar o tenant na chave/metadata e revalidar autorização no download.
- Workers, outbox, retries, importações, notificações, comandos externos, relatórios, busca e Loxi devem receber contexto organizacional explícito e revalidá-lo; nunca reconstruí-lo somente a partir do usuário.
- Cache e chaves de idempotência devem incluir organization_id sempre que o resultado ou recurso for tenant-owned.

### 5.4 Casos mistos e legados

- **notification_preferences:** classificação **MISTO**. `SECURITY` permanece global e obrigatória; `TRIPS` e `OCCURRENCES` são por organização/membership. Derivar a organização ativa da sessão, adicionar `organization_id` e FK composta para membership nas preferências operacionais, substituir a PK atual por identificador substituto e índices UNIQUE parciais, e fazer backfill das preferências operacionais existentes para a organização legada.
- **audit_events:** classificação **MISTO** com escopo `PLATFORM`/`ORGANIZATION`. Fazer backfill por `entity_type` e `changed_fields`, nunca por `actor_id`; operações, perfis, empresa, anexos, importações e outbox existentes vão para a organização legada. Separar `USER_IDENTITY`, `MEMBERSHIP` e `NOTIFICATION_PREFERENCE`; `SECURITY` permanece global, enquanto preferências operacionais são organizacionais. Eventos `USER_*` mistos são divididos por grupo de campos, preservando instante, ator e referência ao ID original; casos ambíguos ficam em quarentena e bloqueiam a ativação.
- **company_profiles:** classificação **LEGADO**. Transferir os seis campos (`legal_name`, `display_name`, `cnpj`, `phone`, `email`, `logo_reference`) para `organizations`; a migration 0036 já copia os três primeiros. Uma migration aditiva deve copiar os três restantes, reconciliar os valores e manter `company_profiles` até que todos os consumidores tenham migrado.
- **users:** manter e-mail/credenciais globais, mas retirar papel/perfil/motorista globais como fonte de autorização após migração para membership.


### 5.5 Reconciliação com a auditoria preliminar da PR #449

A revisão direta dos contratos atuais identificou duas diferenças importantes em relação à classificação preliminar da auditoria:

- **driver_document_types:** a migration 0020 semeia a CNH global reservada, enquanto o endpoint de criação é autorizado por `DriverManager`. A decisão da matriz é **MISTO**: CNH global; tipos customizados pertencem à organização ativa. Tipos customizados existentes serão associados à organização legada, e documentos/políticas precisarão de integridade contextual para impedir uso cruzado.
- **notification_preferences:** o código atual e a interface em Meu Perfil persistem preferências por `user_id/category`, sem contexto de empresa. A ADR-049 e a auditoria da PR #449, porém, definem o split: `SECURITY` global e `TRIPS`/`OCCURRENCES` por organização. A matriz classifica como **MISTO**, exige contexto da sessão e prevê backfill das preferências operacionais para a organização legada.

Essas decisões foram baseadas nos models, services, routers, schemas e migration atuais, e devem ser reconciliadas com o texto da auditoria #449 antes de iniciar migrations de scoping.

## 6. Ordem recomendada de implementação

1. **Congelar o contrato:** aprovar esta matriz e registrar exceções antes de migrations.
2. **Preparar integridade:** adicionar organization_id nullable nas tabelas ORG/HERDADO, índices e FKs compostas sem remover constraints atuais.
3. **Backfill legado:** preencher todas as linhas existentes com o UUID da organização legada em transações controladas; reconciliar contagens, órfãos e relações cruzadas.
4. **Validar antes de NOT NULL:** comparar contagem por tabela, detectar referências incompatíveis e só então aplicar NOT NULL.
5. **Escopar unicidades:** converter índices/constraints globais para escopo organizacional, preservando unicidade de identidade e catálogos globais.
6. **Atualizar autorização e consultas:** repositories → services → rotas/DTOs; membership substitui os campos globais de User como fonte de RBAC.
7. **Cobrir efeitos indiretos:** jobs, workers, outbox, anexos, evidências, relatórios, busca, auditoria, importação e Loxi.
8. **Testar isolamento:** duas organizações com dados parecidos, IDs conhecidos, tentativas de leitura/escrita cruzadas, FK cruzada, cache, retries, arquivos e relatórios.
9. **RLS somente depois:** avaliar como defesa em profundidade após escopo explícito da aplicação; provar com a role real do banco, pool, SET LOCAL, rollback e workers.
10. **Manter feature flag desligada:** onboarding, convite, seletor e operação da segunda organização só entram após aprovação formal do gate de segurança.

## 7. Critérios de aceite desta matriz e da fase seguinte

- [ ] As 53 tabelas existentes estão classificadas, inclusive as duas tabelas declaradas em services.
- [ ] As quatro tabelas da fundação estão documentadas separadamente; total esperado após #449: 57.
- [ ] Todas as tabelas ORG/HERDADO têm organization_id materializado e NOT NULL após backfill.
- [ ] Nenhuma FK entre recursos de negócio permite relação cross-tenant.
- [ ] Chaves de negócio e idempotência têm escopo correto; identidade global permanece global.
- [ ] Casos MISTO e LEGADO têm migração explícita, sem inferência por actor_id.
- [ ] Jobs, anexos, notificações, outbox, relatórios, busca e Loxi preservam o tenant.
- [ ] Testes PostgreSQL 16 provam backfill, contagens, constraints, rollback e isolamento negativo.
- [ ] Segunda organização continua bloqueada até aprovação de segurança e autorização explícita de ativação.

## 8. Fora do escopo desta matriz

Não implementa organization_id, não cria migration, não altera RBAC, não habilita RLS, não cria onboarding/seletor, não executa banco remoto e não realiza merge, deploy ou release. É o contrato de ownership para orientar a implementação incremental da Issue #441.
