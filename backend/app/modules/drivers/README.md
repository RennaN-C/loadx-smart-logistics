# Motoristas

Cadastro do motorista e referência pública usada por viagens. GPS real não faz
parte do MVP.

## Estrutura

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `GET /api/v1/drivers`: lista paginada com `id`, `name`, `license_category`,
  `active` e `created_at`; omite documento, telefone e número da CNH.
- `GET /api/v1/drivers/operational-status`: situação operacional paginada para
  seleção de viagens; expõe `active`, `has_operation_conflict` e `available`
  calculados pela OC67.
- `POST /api/v1/drivers`: cria motorista.
- `GET /api/v1/drivers/{id}`: consulta motorista por ID.
- `PATCH /api/v1/drivers/{id}`: atualiza campos enviados.

`CONFIRMADO`: `ADMIN` e `LOGISTICS_MANAGER` podem consultar. `ADMIN` e `LOGISTICS_MANAGER` podem criar ou atualizar. `CHECKER` e `DRIVER` não acessam o módulo.

## Regras implementadas

- Nome, documento, telefone e CNH são obrigatórios.
- `document` deve ser único.
- `license_number` deve ser único.
- `CONFIRMADO` (OC63): create/update exigem CPF válido e CNH de 11 dígitos,
  validando ambos os verificadores e rejeitando sequências repetidas. CPF
  aceita máscara padrão; CNH aceita somente dígitos. Letras são inválidas.
- `CONFIRMADO`: telefone nacional obrigatório, com 10 ou 11 dígitos e DDD
  não iniciado em zero; celular começa com 9 após o DDD. Máscara de telefone
  é removida. CPF, CNH e telefone novos/alterados são persistidos só com dígitos.
- `CONFIRMADO`: PATCH preserva campos omitidos, mas rejeita `null` em
  documento, CNH e telefone. Falhas usam o erro Pydantic padrão, HTTP `422`.
- `license_category` é opcional e normalizada para maiúsculas quando informada.
- `active = false` representa motorista arquivado para viagens futuras.
- O módulo de viagens bloqueia o motorista durante a criação e rejeita motorista
  inativo.
- O vínculo de identidade fica em `users.driver_id`, não em `drivers`.
- Todas as rotas exigem sessão em cookie e consultam o papel e o estado atual do usuário no banco.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: validação formal da categoria de CNH.

## OC65 — contrato interno consumido pela OC67

`CONFIRMADO`: `DriverService.has_operation_conflict(driver_id,
exclude_trip_id=None)` consulta somente conflito, sem bloquear ou escrever.
`ensure_no_operation_conflict(...)` bloqueia o motorista, valida pela mesma
consulta e retorna `Driver` ou lança `DriverOperationConflictError` com
`driver_id`; motorista inexistente lança `DriverNotFoundError`.
O chamador mantém o bloqueio até o commit/rollback da operação completa.

`CONFIRMADO`: `SCHEDULED` e `IN_ROUTE` reservam; `FINISHED` libera. Plano e
carregamento isolados não reservam motorista. A exclusão serve apenas à própria
viagem em alteração; criação não exclui nenhuma viagem.

`CONFIRMADO`: ausência de conflito não verifica existência, `active` ou acesso
do usuário. A OC67 combina cadastro ativo com esta consulta e expõe a fronteira
interna `FleetAvailabilityService`, sem persistir disponibilidade.

`CONFIRMADO` (OC68): a disponibilidade operacional de caminhões já possui
contrato HTTP em `GET /api/v1/trucks/operational-status`.

`CONFIRMADO` (OC72): `GET /api/v1/drivers/operational-status` espelha a
fronteira já usada pelos caminhões. O endpoint lista os motoristas e consulta
`FleetAvailabilityService.get_driver_availability`; não reproduz a regra de
conflito da OC65 e não persiste disponibilidade.

## OC105 — arquivamento lógico

`CONFIRMADO`: `active=false` significa arquivado, sem DELETE e sem remoção de
referências históricas. PATCH com `active=true` reativa, validando o cadastro
completo e mantendo as unicidades globais. ADMIN e LOGISTICS_MANAGER escrevem.
Alterações de estado registram ator, entidade e campo `active` na auditoria,
na mesma transação; repetições não criam eventos duplicados.

`CONFIRMADO`: a coleção usa `archive_status=active|archived|all`, default
`active`, filtrado no PostgreSQL antes da paginação. Consulta por ID não esconde
arquivados. Os contratos de disponibilidade mantêm a visão de cadastro e
conflito separados; operações existentes preservam histórico e RBAC.

## OC102 — histórico documental e validade CNH

`CONFIRMADO`: models inclui tipos aprovados, versões e políticas. document_*
mantêm regras no módulo; document_history compartilha staging com CRUD atual,
versionando número/categoria/validade e projetando CNH corrente no cadastro.
Migração faz backfill sem inventar validade. Shared/document_validity concentra
a regra temporal da OC101; sem importar tabelas internas de trucks.
DriverService.has_document_conflict(at=...) e ensure_operational_eligibility
compõem reserva/início de viagem e disponibilidade. Categoria aceita é
configuração explícita, sem classificação inferida do veículo; CNH exigida sem
validade/categoria conhecida é inelegível. Tipo adicional aprovado por gestor,
política inicialmente desligada. Constraints/locks/auditoria/rollback preservam
identidade, unicidade CNH e histórico. Sem DELETE/storage/DETRAN/notificação.
ADMIN/LOGISTICS_MANAGER consultam e gerenciam; CHECKER/DRIVER continuam negados.
ADR-032, head 20261009_0020.
