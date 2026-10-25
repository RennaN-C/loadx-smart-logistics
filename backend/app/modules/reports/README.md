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

## Apresentação dos PDFs — manutenção #308

`CONFIRMADO`: `pdf_renderer.py` centraliza a apresentação de carregamento,
viagem e gerencial: cabeçalho LoadX navy/âmbar, identificação em duas colunas,
resumo numérico, tabelas proporcionais e alternadas, emissão UTC e paginação.
O gerencial acrescenta barras relativas ao maior total; os fatos distintos não
são somados. Situações e tipos conhecidos são apresentados em português apenas
nas respectivas colunas, preservando códigos de produto e identificadores.

`CONFIRMADO`: cabeçalhos repetem em páginas subsequentes; linhas maiores que uma
página podem ser divididas. Conteúdo é escapado antes de criar Paragraphs.
Fontes continuam incorporadas pelo ReportLab existente. Nenhuma dependência,
consulta, regra operacional, permissão, endpoint ou formato CSV foi alterado.
O E2E multi-caminhão foi adaptado à nova apresentação do rótulo de contagem,
mantendo as verificações de UUIDs, escopo da parte e índices físicos.

`CONFIRMADO`: exemplos fictícios e resultados em
[relatórios e controles](../../../../docs/evidencias/relatorios-controles/README.md).
