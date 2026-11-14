# Auditoria técnica — fundação multiempresa do LoadX

- **Data:** 14/11/2026
- **Base analisada:** branch `desenvolvimento`, v1.3.0 como linha funcional.
- **Objetivo:** registrar os bloqueios reais para transformar a instalação monoempresa em SaaS multiempresa.
- **Implementação inicial:** Issue #448, branch `feat/fundacao-multiempresa`, migration `20261114_0036`.

## 1. Conclusão executiva

O LoadX ainda é estruturalmente single-tenant. O PostgreSQL possui 51 tabelas
mapeadas pelo ORM, mas os modelos operacionais não carregam um contexto de
organização. Os repositórios fazem consultas por ID, filtros funcionais e
relações sem escopo organizacional. A sessão opaca autentica o usuário, mas
antes da migration 0036 não registrava uma organização ativa.

Adicionar apenas uma coluna no usuário, aceitar `X-Company-ID` ou esconder
menus no frontend não cria isolamento seguro. A ativação de uma segunda empresa
deve permanecer bloqueada até que cada consulta, relação, job e recurso
polimórfico esteja associado e validado contra a organização da sessão.

## 2. Achados por domínio

### Identidade e autorização

- `users.email` é único globalmente, adequado para uma identidade global.
- `users.role`, `users.custom_profile_id` e `users.driver_id` são hoje globais,
  mas representam permissões/vínculos que precisarão ser contextuais por empresa.
- `auth_sessions` tinha apenas `user_id`, hash do token, validade e revogação;
  não existia `active_organization_id`.
- `access_profiles.name_key` é globalmente único. Perfis customizados precisarão
  pertencer a uma organização; `access_permissions` permanece catálogo global.
- `driver_id` em User é globalmente único; o vínculo de motorista deve migrar
  para membership, com unicidade por organização.

### Dados da empresa e domínio logístico

- `company_profiles` usa `PROFILE_ID` fixo e constraint singleton. É cadastro
  da instalação atual, não uma tabela de empresas.
- Clientes, endereços, produtos, motoristas, caminhões, manutenções, documentos,
  pedidos, itens, planejamentos, distribuições, carregamentos, viagens, entregas
  e ocorrências não possuem ownership organizacional.
- `load_distributions`, partes, pedidos, volumes e planos formam relações
  cruzadas; cada FK deverá garantir que os pais e filhos pertençam à mesma empresa.
- `driver_document_types` e `access_permissions` são catálogos compartilhados;
  políticas/documentos operacionais pertencem ao contexto da organização.

### Dados polimórficos e assíncronos

- `status_history` e `audit_events` usam `entity_type/entity_id`; não há FK
  convencional que permita inferir tenant com segurança. Precisam receber
  organization_id no evento, validado na origem.
- `operational_attachments` pode apontar para diferentes tipos de recurso;
  a organização precisa ser validada com o único pai efetivo e em downloads.
- Notificações, destinatários, preferências, outbox, tentativas e comandos de
  reprocessamento precisam herdar e preservar o tenant em cada transição.
- `external_commands`, `registration_imports`, relatórios, busca e Loxi não
  podem confiar apenas no usuário ou em IDs de recursos enviados pelo cliente.
- Triggers e constraints de integridade das migrations 0025–0034 também devem
  validar contexto organizacional quando as colunas forem introduzidas.

## 3. Tabelas e ownership

A auditoria identificou 51 tabelas ORM. Identidade e segurança global incluem
`users` e as tabelas `auth_*`; catálogos compartilhados incluem
`access_permissions` e `driver_document_types`. Os demais registros de negócio,
histórico, documentos, notificações e integrações precisam de ownership por
organização ou de uma decisão explícita de permanecer global (por exemplo,
preferências puramente pessoais).

A classificação final deverá ser registrada antes das migrations de scoping.
Não inferir tenant a partir de `actor_id`: um usuário poderá pertencer a mais
de uma organização.

## 4. Banco, sessão e RLS

- `get_db()` cria uma Session SQLAlchemy por request; atualmente não instala
  contexto organizacional na transação.
- `infra/database/production_roles.sql` separa o papel de aplicação do papel
  administrativo e define o usuário de aplicação sem privilégios de superuser.
  Ainda é necessário comprovar que a conexão real do Render usa esse papel.
- Não foram encontradas políticas RLS de tenant ativas. RLS deve ser defesa
  adicional depois que o backend aplicar escopo explícito e cada transação/
  worker instalar contexto via mecanismo seguro e transacional.
- Nunca usar contexto de conexão persistente sem reset garantido: pool,
  rollback, workers e sessões reutilizadas podem vazar tenant.

## 5. Fundação entregue na migration 0036

- `organizations`: organização e estado comercial/operacional.
- `organization_memberships`: vínculo de usuário, role, perfil customizado,
  motorista e status por empresa.
- `organization_invitations`: token armazenado somente como hash, validade,
  aceite e revogação.
- `platform_owner_grants`: singleton que permite no máximo um proprietário
  geral. A migration não concede o grant automaticamente.
- `auth_sessions.active_organization_id`: contexto derivado no backend e FK
  composta para garantir membership do usuário.
- Backfill: uma organização legada é criada a partir de `company_profiles`;
  usuários e sessões existentes são associados a ela, preservando UUIDs e
  atributos atuais.
- UserService mantém a membership legada sincronizada durante a transição.

## 6. Limites atuais — bloqueadores de ativação

A fase 1 **não** adiciona ainda `organization_id` aos recursos de domínio
restantes, não altera o RBAC para membership contextual, não cria endpoint de
seleção/troca de empresa, não libera onboarding e não ativa RLS. O campo de
organização na sessão ainda não é consumido por todos os repositórios.

Até concluir as fases seguintes:
- manter uma única organização operacional;
- não criar usuários em outra organização;
- não expor convite, seletor ou onboarding;
- não habilitar RLS parcialmente;
- não fazer deploy de migrations em banco remoto sem aprovação.

## 7. Próximas fases técnicas

1. Fechar inventário de ownership por tabela, inclusive preferências e catálogos.
2. Adicionar organization_id aos recursos tenant-owned, com backfill determinístico.
3. Criar chaves únicas compostas e FKs compostas em todas as relações entre recursos.
4. Atualizar repositories, services, rotas, relatórios, busca, anexos, auditoria,
   notificações, outbox, integrações e Loxi para exigir contexto organizacional.
5. Mover role, custom_profile_id e driver_id de User para membership como fonte
   de autorização, mantendo migração de compatibilidade auditável.
6. Aplicar contexto transacional no backend e workers; depois testar RLS com o
   papel real de aplicação e conexões reutilizadas.
7. Testar duas organizações com IDs conhecidos, UUIDs cruzados, relatórios,
   anexos, jobs, notificações, Loxi e concorrência.
8. Só então implementar onboarding, convite, seletor de empresa e habilitação
   comercial sob feature flag.

## 8. Testes obrigatórios antes da ativação

- Backfill preserva contagens, UUIDs, FKs e histórico.
- Toda FK entre recursos tenant-owned inclui organização na integridade.
- Tentativas cross-tenant por UUID, busca, filtros, relatórios e anexos falham
  sem revelar existência de dados.
- Jobs/outbox/retries mantêm o tenant correto entre processos.
- Troca/revogação de membership invalida contexto/sessão de forma determinística.
- RLS não permite acesso sem contexto, com contexto anterior ou por papel de
  banco que ignore políticas.
- Backup e rollback são ensaiados em banco isolado PostgreSQL 16.
