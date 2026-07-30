# Histórico de status

Registro auditável das mudanças de status das entidades operacionais.

## Estrutura

- `models.py`: entidade SQLAlchemy `StatusHistory`.
- `schemas.py`: contratos Pydantic `StatusHistoryCreate` e `StatusHistoryRead`.
- `repository.py`: consultas e persistência de histórico.
- `service.py`: registro e consulta interna de histórico.

Crie somente os arquivos necessários para a ocorrência atual.

## Regras implementadas

- Cada registro possui `entity_type`, `entity_id`, `new_status` e `created_at`.
- `old_status` é opcional para o primeiro status conhecido.
- `changed_by` é opcional e aponta para `users.id` quando houver usuário responsável.
- Quando `changed_by` é informado, o usuário deve existir.
- `entity_type`, `old_status` e `new_status` são normalizados para maiúsculas.

## API

`PENDENTE DE DEFINIÇÃO`: não há endpoint público de consulta de histórico em `docs/05-contratos-api.md`.

`RECOMENDAÇÃO`: até existir contrato aprovado, outros services devem usar `StatusHistoryService.record_status_change`.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: lista final de `entity_type` permitidos.
- `PENDENTE DE DEFINIÇÃO`: se o histórico será público por API e quais perfis poderão consultar.
