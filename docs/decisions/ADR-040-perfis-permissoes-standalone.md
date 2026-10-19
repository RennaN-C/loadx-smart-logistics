# ADR-040: permissões efetivas e perfis locais personalizados

Status: proposta implementada para revisão na OC112 (#159).

## Contexto e inventário

`CONFIRMADO`: a base 37e6ce5 integra OC86 (#217), Aparência e Busca global.
ADR-038 pertence à OC98 isolada; não é incorporada. Os routers já permitem
ADMIN na maioria das ações gerenciais. Autorização por papel ainda existe em
routers, escopos de viagens, anexos, importação, auditoria e busca global.
A migração será por ação, preservando essas fronteiras, não por substituição
indiscriminada de papéis.

## Decisão de migração

- Catálogo fechado e tipado `loadx.<recurso>.<ação>`, documentado no módulo
  access_profiles. Nenhuma regra executável ou permissão enviada pelo cliente
  é usada para autorizar a própria requisição.
- Os quatro papéis fixos mantêm seus identificadores e projeções em código.
  ADMIN inclui gestão logística, sem poderes de plataforma ou personificação.
  CHECKER mantém leitura operacional/conferência; DRIVER mantém somente ações
  próprias sujeitas a vínculo ativo. Meu perfil continua sendo por identidade.
- Perfil personalizado é uma entidade UUID com nome único sem distinção de
  caixa, descrição, estado e versão para concorrência otimista. Um usuário
  recebe exatamente um papel fixo OU `CUSTOM` com `custom_profile_id`; não há
  união de privilégios com LOGISTICS_MANAGER. Vínculo de motorista é exclusivo
  de DRIVER. Perfis do sistema são projeções imutáveis, não editáveis via API.
- Permissões reservadas de identidade, configuração, integrações administrativas
  e auditoria não são delegáveis. Ações próprias DRIVER também não são
  delegáveis. Carregamento delegado exige operador autenticado e preserva as regras de
  conferência, sem personificação. A auditoria existente não é ampliada nesta OC.
- Grants desconhecidos/reservados são recusados pelo service e por FK composta
  do catálogo no PostgreSQL. Ausência de permissão nega por padrão com 403.
- Permissão de gestão não implica leitura: ambas devem ser selecionadas quando
  necessárias. Formulário indica as permissões e suas descrições explicitamente.
- Perfis não são excluídos. Desativação em uso é 409; remover vínculos primeiro.
  Alterar grants ou associação revoga todas as sessões afetadas no mesmo commit
  da alteração e da auditoria. Mudança concorrente de versão é 409.
- Mutações de perfil e associação são serializadas por advisory lock transacional
  PostgreSQL; usuários afetados são bloqueados em ordem de UUID antes do perfil,
  depois sessões. Autorização CUSTOM relê usuário e perfil sob SHARE durante a
  operação. Associação revalida perfil ativo sob lock. Isso evita grants obsoletos
  e associação concorrente a perfil que está sendo desativado.
- Backfill não reclassifica nenhum usuário: perfil nulo mantém o papel legado.
  A migration inclui catálogo estático e constraints, sem OC98. Downgrade
  falha explicitamente se houver usuário CUSTOM, evitando perda de acesso;
  reassociar usuários a papéis fixos antes do rollback.
- Logs/auditoria contêm UUIDs e nomes de campos, nunca credenciais ou valores.
  Auditoria administrativa de perfis permanece ADMIN-only.

## Etapas e limites

1. Persistir catálogo/perfis/grants e expor administração ADMIN-only.
2. Ampliar associação de usuário e projeção de permissões em login/me.
3. Migrar cada ação de domínio, preservando vínculo/estado/histórico e o recorte
   de CHECKER para planos aprovados. Busca consulta apenas categorias autorizadas.
4. Consumir a projeção no frontend e integrar perfis à OC86; testar API direta,
   sessões, concorrência, migration, UI e regressões.

`CONFIRMADO`: standalone, sem tenant, entitlement, SUPERADMIN, licenciamento,
SSO, SMTP, recuperação ou MFA. Futuro contexto CoreFlow deverá ser validado em
camada externa e nunca será concedido por uma permissão local. A PR permanece
aberta para revisão; sem merge ou deploy automático.
