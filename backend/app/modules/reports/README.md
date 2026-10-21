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


## OC90 — fluxo multi-caminhão

`CONFIRMADO`: Os PDFs de carregamento e viagem acrescentam distribuição/parte, plano e
quantidade de volumes quando existe distribuição. Ambos preservam identidades
(order_item_id, volume_index) do próprio plano; a viagem também lista os volumes
transportados. Dados vêm do plano persistido e da fronteira pública de
load_planning, sem acesso privado, escrita ou recálculo. Legado não exige parte.
Teste E2E extrai o texto real do PDF com pypdf (dependência apenas de testes).
