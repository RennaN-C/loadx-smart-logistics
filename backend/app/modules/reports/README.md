# Relatórios

Geração de relatórios de plano, carregamento e entrega. Preferir serviço separado da rota HTTP.

## Estado atual

`CONFIRMADO`: os endpoints `GET /api/v1/reports/load-plans/{id}` e
`GET /api/v1/reports/trips/{id}` retornam PDF como download. O primeiro inclui
plano, caminhão, volumes, sequência, conferência, início, fim e status; o segundo
inclui viagem, caminhão, entregas, status, ocorrências e datas.

`CONFIRMADO`: os relatórios consultam dados persistidos e não recalculam nem
alteram plano, carregamento, viagem ou entrega.

## Estrutura

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.
