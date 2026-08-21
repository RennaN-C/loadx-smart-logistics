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
- `changed_by` é opcional e aponta para `users.id` quando houver usuário
  responsável.
- Quando `changed_by` é informado, o usuário deve existir.
- `entity_type`, `old_status` e `new_status` são normalizados para maiúsculas.
- `entity_type` aceita somente `ORDER`, `LOAD_PLAN`, `TRIP` e `DELIVERY`, também
  protegido por check constraint no PostgreSQL.
- A criação manual de pedido registra `ORDER`, `null -> DRAFT` e o usuário
  responsável.
- Cada transição efetiva de pedido gera exatamente um registro; repetição do
  status atual não gera outro registro.
- Criação e transições efetivas de viagens e entregas reutilizam o mesmo padrão;
  mudanças de pedido associadas ficam no mesmo commit.

## API

`CONFIRMADO` por D10: não há endpoint público de consulta de histórico na OC09.

`CONFIRMADO`: operações independentes usam `record_status_change`. Uma operação
que precisa compartilhar transação com outro agregado usa `stage_status_change`
e deixa o service externo executar um único commit ou rollback.

`CONFIRMADO`: D05 exige que a alteração do agregado e o histórico compartilhem
uma única transação; falha em qualquer etapa desfaz ambas.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: contrato, filtros e perfis de uma eventual consulta
  protegida em ocorrência futura.
