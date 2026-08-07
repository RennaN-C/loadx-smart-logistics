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

`CONFIRMADO`: `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem consultar. Somente `LOGISTICS_MANAGER` pode criar ou atualizar. `DRIVER` não acessa o módulo enquanto não existir vínculo aprovado com o caminhão.

## Regras implementadas

- Placa é normalizada para maiúsculas.
- Placa deve ser única.
- Dimensões internas e peso máximo devem ser maiores que zero.
- `max_weight_kg` permanece `Decimal` internamente e usa exclusivamente número
  JSON na entrada e na saída, conforme D06 e ADR-016.
- Exclusão física ainda não foi implementada; use `active = false` para indisponibilidade.
- Todas as rotas exigem autenticação Bearer e consultam o papel e o estado atual do usuário no banco.
