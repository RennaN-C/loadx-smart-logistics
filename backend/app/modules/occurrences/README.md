# Ocorrências

Registro de avaria, cliente ausente, recusa, atraso e outros eventos.

## Estado atual

`CONFIRMADO`: `POST /api/v1/occurrences` registra texto obrigatório e URL de
foto opcional, vinculados a uma viagem e, quando informado, a uma entrega da
mesma viagem.

`CONFIRMADO`: `GET /api/v1/trips/{trip_id}/occurrences` consulta o histórico sem
sobrescrever eventos. `LOGISTICS_MANAGER` opera qualquer viagem; `DRIVER`
opera e consulta somente a própria; `ADMIN` apenas consulta.

## Estrutura

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.
