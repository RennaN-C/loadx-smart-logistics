# Organizações — fundação SaaS

Este módulo é proprietário do registro de organizações, memberships, convites e
concessão do proprietário da plataforma.

## Fase 1 — registro e identidade contextual

- `Organization`: organização comercial e estado de ciclo de vida.
- `OrganizationMembership`: vínculo de usuário, papel, perfil customizado,
  motorista e estado dentro de uma organização.
- `OrganizationInvitation`: convite de uso único; somente o hash do token é
  persistido, com expiração, aceite e revogação auditáveis.
- `PlatformOwnerGrant`: concessão singleton para o único proprietário da
  plataforma. A migration não cria nem escolhe automaticamente esse usuário.
- `LEGACY_ORGANIZATION_ID`: identidade estável da organização que recebe os
  dados e usuários já existentes.

Nesta fase, a membership legada espelha os campos de compatibilidade em
`users.role`, `users.custom_profile_id` e `users.driver_id`. O RBAC atual ainda
usa `User`; memberships ainda não autorizam acesso a recursos de negócio.

A sessão recebe `active_organization_id` somente quando o servidor encontra
membership e organização ativas. O valor nunca é aceito de header, query string
ou payload do cliente. Sessões com membership suspensa/removida ou organização
inativa são recusadas.

## Limites de segurança desta fase

A aplicação continua operando em uma única organização. Ainda não há endpoints
de solicitação/aprovação, convite, seleção ou troca de empresa. Os agregados
logísticos ainda não possuem `organization_id`; os repositórios ainda não estão
escopados e RLS não foi habilitado. Não cadastrar uma segunda organização nem
ativar multiempresa até concluir o scoping integral de dados, APIs, jobs,
relatórios, anexos, auditoria, notificações e Loxi.
