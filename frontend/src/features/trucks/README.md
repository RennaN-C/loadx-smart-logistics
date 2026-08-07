# Feature: trucks

Listagem e cadastro de caminhões (OC26). Consome `GET/POST/PATCH /trucks`.

## O que existe hoje

- `pages/TruckListPage.tsx` (+ `.css`): grid de cards, busca e filtro de status **client-side**
  (o backend ainda não aceita query params), estados de carregando/vazio/erro e o modal de cadastro.
- `components/TruckCard.tsx`: placa, modelo, status, desenho técnico e specs de um caminhão.
- `components/TruckForm.tsx`: criação e edição, com pré-visualização do desenho e do volume interno
  atualizando conforme as medidas são digitadas.
- `components/TruckSchematic.tsx` + `truckGeometry.ts`: desenho técnico do baú (vista lateral e traseira),
  proporcional às medidas reais. A geometria fica isolada em funções puras, testadas à parte.
- `components/trucksErrorMessages.ts`: tradução dos códigos de erro do backend.
- `api/trucksApi.ts`: mapeamento snake_case ↔ camelCase.
- `hooks/useTrucks.ts`: carga da lista + `refetch`.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem a lista. Só `LOGISTICS_MANAGER` cria e edita — a UI
esconde "Novo caminhão" e "Editar" para os demais, mas quem barra de verdade é o backend.

## Fora de escopo nesta ocorrência

Paginação e busca server-side (não suportadas pelo backend) e exclusão física (não existe rota;
desativar é `active: false` via PATCH).
