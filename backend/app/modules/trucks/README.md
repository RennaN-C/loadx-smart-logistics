# Caminhões

Dimensões internas, peso máximo, disponibilidade e validações do veículo.

## Estrutura

- `models.py`: entidade SQLAlchemy `Truck`.
- `schemas.py`: contratos Pydantic `TruckCreate`, `TruckUpdate` e `TruckRead`.
- `repository.py`: consultas e persistência de caminhões.
- `service.py`: regras de placa única, criação, consulta e atualização.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `GET /api/v1/trucks`: lista caminhões no envelope paginado da ADR-017.
- `POST /api/v1/trucks`: cria caminhão.
- `GET /api/v1/trucks/{id}`: consulta caminhão por ID.
- `PATCH /api/v1/trucks/{id}`: atualiza campos enviados.

`CONFIRMADO`: `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem consultar. Somente
`LOGISTICS_MANAGER` pode criar ou atualizar. `DRIVER` não acessa os endpoints do
módulo na API atual.

## Regras implementadas

- Placa é normalizada para maiúsculas.
- Placa deve ser única.
- Dimensões internas e peso máximo devem ser maiores que zero.
- `max_weight_kg` permanece `Decimal` internamente e usa exclusivamente número
  JSON na entrada e na saída, conforme D06 e ADR-016.
- Exclusão física ainda não foi implementada; use `active = false` para indisponibilidade.
- Todas as rotas exigem sessão em cookie e consultam o papel e o estado atual do usuário no banco.

## OC64 — conflito operacional

`CONFIRMADO`: o módulo de caminhões centraliza a regra reutilizável de conflito
operacional.

`TruckService.has_operation_conflict(...)` executa a consulta somente de
conflito e pode ignorar o próprio `load_plan_id` da operação consultada.

`TruckService.ensure_no_operation_conflict(...)` bloqueia a linha do caminhão
para atualização antes da consulta e lança `TruckOperationConflictError` quando
outra operação ativa utiliza o mesmo veículo.

A regra considera carregamento e viagem:

- plano sem artefato operacional não causa conflito;
- sessão de carregamento mantém a reserva enquanto a viagem não estiver
  `FINISHED`;
- viagem `SCHEDULED` ou `IN_ROUTE` causa conflito;
- viagem `FINISHED` libera o caminhão;
- o mesmo `load_plan_id` não conflita consigo próprio.

`IMPORTANTE`: ausência de conflito não significa disponibilidade completa.
`Truck.active` continua sendo uma regra independente. A OC67 deve combinar o
estado cadastral do caminhão com esta consulta, sem acessar diretamente as
tabelas de carregamento ou viagens e sem duplicar a regra.

## OC68 — status operacional dos caminhões

`GET /api/v1/trucks/operational-status` expõe uma listagem paginada da situação
operacional atual dos caminhões.

O endpoint usa a mesma paginação de `GET /api/v1/trucks` e pode ser consultado
por:

- `ADMIN`;
- `CHECKER`;
- `LOGISTICS_MANAGER`.

`DRIVER` não possui acesso.

Cada item contém:

- `id`;
- `plate`;
- `model`;
- `active`;
- `has_operation_conflict`;
- `available`.

`active`, `has_operation_conflict` e `available` são obtidos por meio da
fronteira `FleetAvailabilityService` criada na OC67. O router e o serviço da
OC68 não reproduzem as regras de conflito da OC64.

A disponibilidade continua sendo calculada em tempo de leitura e não é
persistida no banco.

Respostas de erro seguem o contrato padrão da API:

- `401`: sessão ausente ou inválida;
- `403`: usuário sem permissão ou inativo;
- `422`: parâmetros de paginação inválidos.

A resposta vazia continua usando o envelope paginado, com `items = []`,
`total = 0` e `total_pages = 0`.

Este contrato é a fronteira de leitura destinada ao painel da OC73.
