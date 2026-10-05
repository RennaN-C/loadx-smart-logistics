# Feature: trucks

Listagem e cadastro de caminhões (OC26) e o painel de situação da frota (OC73).
Consome `GET/POST/PATCH /trucks` e `GET /trucks/operational-status`.

## O que existe hoje

- `pages/TruckListPage.tsx` (+ `.css`): grid paginado de cards, busca e filtro de
  status **client-side na página atual**, estados de carregando/vazio/erro e o
  modal de cadastro.
- `components/TruckCard.tsx`: placa, modelo, status, desenho técnico e specs de um caminhão.
- `components/TruckForm.tsx`: criação e edição, com pré-visualização do desenho e do volume interno
  atualizando conforme as medidas são digitadas.
- `components/TruckSchematic.tsx`: ilustração do baú (vista lateral e traseira) com as cotas do cadastro.
  As imagens ficam em `frontend/public/trucks/` e são **fixas**: não deformam conforme as medidas. O que
  muda é só o valor das cotas ao lado do desenho — decisão de produto, o desenho situa quem cadastra e o
  número é que carrega a informação. As imagens são decorativas (`alt=""`), então nada de acessibilidade
  depende delas.

  Ficam em `public/` (e não em `src/assets/`) de propósito: assim uma imagem ausente não quebra o build.
  Devem ser PNG com fundo transparente e recortadas na silhueta do caminhão — o CSS as encaixa com
  `object-fit: contain` e `object-position: bottom`, para as duas vistas ficarem apoiadas no mesmo chão.
- `pages/FleetStatusPage.tsx` (+ `.css`): painel de situação da frota em `/fleet` (OC73).
- `components/fleetStatusLabels.ts`: como a situação do caminhão vira rótulo e tom.
- `components/trucksErrorMessages.ts`: tradução dos códigos de erro do backend.
- `api/trucksApi.ts`: mapeamento snake_case ↔ camelCase.
A carga paginada vem de `hooks/useResourceList` (compartilhado). O `useTrucks` desta feature
deixou de existir quando o hook virou genérico, na OC28.

`CONFIRMADO`: `max_weight_kg` é consumido e enviado como `number`, sem união com
`string` ou coerção no adapter, conforme D06 e ADR-016.

## Painel de situação da frota (OC73)

`CONFIRMADO`: `GET /trucks/operational-status` devolve, por caminhão, `active`,
`has_operation_conflict` e `available`. O `available` chega **calculado** —
`fleet/service.py` o compõe a partir das regras de conflito da OC64, que
pertencem ao módulo de caminhões.

**A tela não refaz essa conta.** `active` e `has_operation_conflict` servem só
para EXPLICAR por que um caminhão não está disponível. Repetir a fórmula aqui
criaria uma segunda fonte de verdade, e no dia em que a regra mudar no backend a
frota pareceria uma coisa neste painel e outra no planejamento. Há teste que
passa uma combinação impossível pela regra de hoje (conflito **e** disponível) e
exige que a tela obedeça.

Os dois motivos podem valer ao mesmo tempo — caminhão inativo que ainda está
numa operação —, e nesse caso os dois aparecem. Quando o backend recusa sem
apontar motivo que esta tela conheça, ela diz "Indisponível" e para: inventar
causa seria pior que não explicar.

Os contadores valem para a **página carregada**, e a frase na tela diz isso. D12
mantém filtro e agregação server-side fora do contrato, e "3 de 6 disponíveis"
sem a ressalva passaria por total da frota.

O item fica em **Operação** no menu, não em Cadastros: a situação muda sozinha
durante o dia, o caminhão em si não.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem a lista. Só `LOGISTICS_MANAGER` cria e edita — a UI
esconde "Novo caminhão" e "Editar" para os demais, mas quem barra de verdade é o backend.

`CONFIRMADO`: a listagem consome o envelope e os parâmetros da ADR-017. Busca e
filtros server-side continuam fora do contrato por D12.

## Fora de escopo nesta ocorrência

Busca server-side e exclusão física (não existe rota; desativar é
`active: false` via PATCH).
