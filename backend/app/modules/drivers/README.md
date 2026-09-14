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
- `POST /api/v1/drivers`: cria motorista.
- `GET /api/v1/drivers/{id}`: consulta motorista por ID.
- `PATCH /api/v1/drivers/{id}`: atualiza campos enviados.

`CONFIRMADO`: `ADMIN` e `LOGISTICS_MANAGER` podem consultar. Somente `LOGISTICS_MANAGER` pode criar ou atualizar. `CHECKER` e `DRIVER` não acessam o módulo.

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
- `active = false` representa motorista indisponível para viagens futuras.
- O módulo de viagens bloqueia o motorista durante a criação e rejeita motorista
  inativo.
- O vínculo de identidade fica em `users.driver_id`, não em `drivers`.
- Todas as rotas exigem sessão em cookie e consultam o papel e o estado atual do usuário no banco.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: validação formal da categoria de CNH.

## OC65 — contrato interno para OC67/OC72

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
do usuário. A OC67 deve combinar cadastro ativo com esta consulta; a OC72 deve
consumir o contrato HTTP de disponibilidade a definir, sem reproduzir a regra.
`PENDENTE DE DEFINIÇÃO`: endpoint de disponibilidade pertence à OC67/OC72.
