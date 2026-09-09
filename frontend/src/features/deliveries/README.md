# Feature: deliveries

Acompanhamento de viagem e entregas (OC34). Consome `GET /trips`, `POST /trips`, `GET /trips/{id}`,
`PATCH /trips/{id}/status` e `PATCH /deliveries/{id}/status`.

## O que existe hoje

- `pages/TripPage.tsx` (+ `.css`): a rota `/trips/:tripId` — situação da viagem, paradas na ordem da
  rota e as ações que avançam o ciclo.
- `components/CreateTripAction.tsx`: cria a viagem a partir de um plano de carga **aprovado**.
- `components/tripLabels.ts`: rótulos de situação e o verbo de cada ação.
- `components/tripsErrorMessages.ts`: tradução dos 15 códigos de erro do módulo.
- `api/tripsApi.ts`: mapeamento snake_case ↔ camelCase.

## Ciclos de mão única

O backend não permite voltar atrás nem pular etapa (`TRIP_STATUS_TRANSITIONS` e
`DELIVERY_STATUS_TRANSITIONS`):

| viagem | entrega |
|---|---|
| `SCHEDULED` → `IN_ROUTE` → `FINISHED` | `PENDING` → `IN_DELIVERY` → `DELIVERED` |

Por isso a tela mostra **um botão só**, com o verbo da próxima etapa ("Iniciar viagem", "Confirmar
entrega") em vez de um seletor de situação: não há escolha a fazer.

Duas travas do backend viram estado visível na tela, não erro depois do clique:

- entrega só se movimenta com a viagem `IN_ROUTE` (`DELIVERY_TRIP_NOT_IN_ROUTE`) — antes disso os
  botões ficam desabilitados e a tela explica;
- viagem só finaliza com todas as entregas concluídas (`TRIP_DELIVERIES_NOT_FINISHED`) — o botão fica
  desabilitado enquanto houver parada em aberto.

## Como se chega aqui

Por dois caminhos.

**Criando**, a partir do plano de carga aprovado: `PlanSummary` mostra "Criar viagem" quando o plano
está `APPROVED`, e depois de criada a viagem vive em `/trips/:tripId`.

**Pela lista**, com `GET /trips` paginado. `ADMIN` e `LOGISTICS_MANAGER` veem todas; `DRIVER` recebe
**somente as dele** — o recorte é feito em `deliveries/service.py`, não no frontend. Repetir esse
filtro aqui seria duplicar no cliente uma regra de acesso que já é aplicada onde importa.

`CONFIRMADO`: o `DRIVER` tinha ficado sem porta de entrada enquanto a listagem não existia, e o
painel dele abria com contadores que respondiam 403. Agora a tela inicial do motorista lista as
viagens dele, com carregando, vazio, erro e link para cada uma.

## Carregamento e início da viagem

`CONFIRMADO`: o backend possui carregamento persistido, checklist e finalização.
`LoadingReferenceService` libera `SCHEDULED -> IN_ROUTE` quando a sessão do
mesmo plano está `FINISHED`; ausência ou incompletude retorna
`TRIP_LOADING_NOT_FINISHED`. O fluxo positivo está coberto por
`backend/tests/e2e/test_complete_flow.py`.

`RISCO IDENTIFICADO`: `components/tripsErrorMessages.ts` ainda afirma que o
carregamento não existe ao traduzir esse erro. O texto está desatualizado e foi
registrado para correção própria, preservando o comportamento nesta preparação.

`CONFIRMADO`: `PATCH /deliveries/{id}/status` retorna somente `DeliveryRead`.
`changeDeliveryStatus` interpreta essa resposta como `DeliveryDto`, mapeia a
entrega e usa seu `trip_id` para recarregar `GET /trips/{trip_id}`. O hook
`useTripPage` substitui o estado pela viagem completa desse GET, sem reconstrução
parcial no navegador. A assinatura pública do adapter continua `Promise<Trip>`;
`TripPage` permanece compatível e é seu único consumidor de produção.

`CONFIRMADO`: falha no PATCH não dispara GET. Falha no GET posterior propaga o
erro para a tela, preserva o último estado conhecido e não repete automaticamente
o PATCH; a alteração pode já estar persistida e uma recarga da página consulta
o estado atual. Os testes `api/tripsApi.test.ts` e
`pages/TripPage.integration.test.tsx` cobrem contratos, erros e o ciclo
`PENDING -> IN_DELIVERY -> DELIVERED` com adapter e hook reais.

## Permissões

Ler: `ADMIN`, `LOGISTICS_MANAGER` e `DRIVER`. Operar (mover viagem e entregas):
`LOGISTICS_MANAGER` e `DRIVER`. Criar viagem: só `LOGISTICS_MANAGER`.

O motorista só enxerga a própria viagem — o backend confere pelo vínculo `users.driver_id`, criado na
`OC09`. A tela não tenta replicar essa checagem; um acesso indevido volta `AUTH_FORBIDDEN` e a
mensagem diz que a viagem não é sua.
