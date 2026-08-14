# Feature: deliveries

Acompanhamento de viagem e entregas (OC34). Consome `POST /trips`, `GET /trips/{id}`,
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

**O backend não lista viagens** — só `POST /trips` e `GET /trips/{id}`. A porta de entrada é o plano
de carga aprovado: `PlanSummary` mostra "Criar viagem" quando o plano está `APPROVED`, e depois de
criada a viagem vive em `/trips/:tripId`.

`RISCO IDENTIFICADO`: sem rota de listagem, **um motorista não tem como encontrar a própria viagem**
pela interface — ele depende de receber o link. O caminho previsto é a notificação por WhatsApp
(`OC36`-`OC40`), mas enquanto isso não existir, ou o backend precisa de um `GET /trips` filtrado pelo
motorista logado, ou o perfil `DRIVER` fica sem porta de entrada.

## Bloqueio conhecido: nenhuma viagem inicia hoje

Validado contra a API real em 2026-08-09: `PATCH /trips/{id}/status` com `IN_ROUTE` responde
**409 `TRIP_LOADING_NOT_FINISHED`** — *"A viagem só pode iniciar após a finalização do carregamento."*

O módulo `loading` do backend ainda é um **stub vazio** (só `README.md` e `__init__.py`), então não
existe como finalizar carregamento. Na prática **toda viagem fica presa em `SCHEDULED`**, e com ela o
ciclo de entregas, que exige a viagem em rota.

A tela está correta e trata o erro, mas a mensagem foi escrita para explicar a situação em vez de
repetir o backend — sem isso o usuário ficaria tentando descobrir o que fazer. Quando o módulo de
carregamento existir, a mensagem deve voltar a ser só a tradução do código.

O que **foi** validado ao vivo: criação da viagem a partir do plano aprovado, recusa de plano não
aprovado, recusa de plano já em viagem, chaves de viagem e entrega batendo com os DTOs, situação
inicial `SCHEDULED`/`PENDING`, recusa de entrega antes da viagem em rota e recusa de transição pulando
etapa.

## Permissões

Ler: `ADMIN`, `LOGISTICS_MANAGER` e `DRIVER`. Operar (mover viagem e entregas):
`LOGISTICS_MANAGER` e `DRIVER`. Criar viagem: só `LOGISTICS_MANAGER`.

O motorista só enxerga a própria viagem — o backend confere pelo vínculo `users.driver_id`, criado na
`OC09`. A tela não tenta replicar essa checagem; um acesso indevido volta `AUTH_FORBIDDEN` e a
mensagem diz que a viagem não é sua.
