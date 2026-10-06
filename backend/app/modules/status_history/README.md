# Histórico e auditoria

Módulo responsável pelo histórico operacional de status e pela consulta de auditoria da OC97.

## Estrutura

- `models.py`: `StatusHistory` e `AuditEvent`.
- `schemas.py`: contratos internos e resposta unificada da auditoria.
- `repository.py`: persistência e consulta paginada com filtros.
- `service.py`: histórico operacional e auditoria administrativa.
- `router.py`: consulta somente leitura em `GET /api/v1/audit`.

## Histórico operacional

- `status_history` continua registrando `ORDER`, `LOAD_PLAN`, `TRIP` e `DELIVERY`.
- mudanças do agregado e do histórico compartilham a mesma transação;
- `changed_by` aponta para o usuário responsável quando a ação é manual;
- ações automáticas podem usar ator nulo;
- repetição idempotente de estado não cria histórico duplicado.

## Auditoria administrativa — OC97

- `audit_events` complementa o histórico operacional sem alterar registros existentes;
- a primeira entrega registra `USER_CREATED` e `USER_UPDATED`;
- somente nomes de campos alterados são persistidos; valores pessoais, senhas,
  tokens e payloads completos não são copiados para a auditoria;
- criação/alteração de usuário e respectivo evento administrativo são gravados
  no mesmo commit;
- a consulta unificada é somente leitura e permitida a `ADMIN` e
  `LOGISTICS_MANAGER`;
- filtros por entidade, registro, ator, evento e período são aplicados no backend
  antes da paginação.
