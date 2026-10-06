# ADR-024: comprovante operacional a partir da conclusão da entrega

Status: aceita (OC78; aprovada na revisão do PR #98)

## Contexto

`CONFIRMADO`: a ADR-022 já define a conclusão `IN_DELIVERY -> DELIVERED`,
`Delivery.delivered_at` em UTC e o histórico com o usuário responsável, no
mesmo commit que conclui o pedido. A Issue #60 pediu a base operacional do
comprovante, sem evidências reais nem novos estados.

## Decisão

`CONFIRMADO`: representar o comprovante como projeção desses dados existentes,
sem tabela, coluna ou migration. Não há um segundo registro independente de
comprovante: o registro durável é a própria conclusão auditada da entrega.

- `id`: UUID do único histórico `DELIVERY`, `IN_DELIVERY -> DELIVERED`.
- `delivery_id`, `trip_id`, `order_id`: vínculos obtidos da entrega persistida.
- `driver_id`: motorista atribuído à viagem, distinto do usuário que operou.
- `delivered_at`: horário da entrega, sem substituí-lo pelo horário da consulta.
- `recorded_at`: horário do histórico; pode diferir de `delivered_at`.
- `recorded_by`: UUID de `changed_by`, nunca escolhido pelo cliente.

`CONFIRMADO`: `POST /api/v1/deliveries/{id}/receipt`, com corpo `{}`, reutiliza
a conclusão já permitida pelo `TripService`. Não inicia uma entrega `PENDING`,
não salta estados e não finaliza viagem. O comprovante é montado antes do commit;
falha de histórico ou projeção desfaz entrega, pedido e histórico.

`CONFIRMADO`: repetir a operação retorna `200` com o mesmo comprovante,
inclusive após `FINISHED`, preservando a idempotência da ADR-022. A operação
continua exigindo autorização para operar; outro operador autorizado não
substitui o responsável original.

`CONFIRMADO`: `GET /api/v1/deliveries/{id}/receipt` consulta essa projeção,
inclusive quando a entrega foi concluída pelo endpoint de status ou simulador
existentes. Não cria histórico nem expõe histórico geral. Histórico ausente,
ambíguo ou sem responsável falha fechado, sem reconstrução ou backfill fictício.

`CONFIRMADO`: os perfis seguem a operação existente: `LOGISTICS_MANAGER` opera
e consulta; `ADMIN` consulta; `DRIVER` opera e consulta somente a própria viagem
com vínculo/motorista ativos; `CHECKER` não acessa. Sessão, Origin e CSRF são
preservados. A autorização por objeto precede a consulta ao histórico.

## Consequências e evolução

`CONFIRMADO`: não se altera o modelo aprovado nem o contrato dos endpoints
existentes. Os endpoints e schemas aditivos estão em `docs/05`.

`PENDENTE DE DEFINIÇÃO`: nome/documento do recebedor, correção do comprovante,
foto, upload/storage, assinatura, geolocalização e retenção externa exigem
requisitos e aprovação próprios. Não há campos ou URLs de evidência nesta versão,
nem mesmo referências mock. A futura evidência poderá se vincular ao
`delivery_id` sem reinterpretar `id` como identificador de arquivo.

`RISCO IDENTIFICADO`: o histórico atual é polimórfico e `changed_by` é anulável.
O service valida proveniência e unicidade da conclusão; dados legados incompletos
não produzem comprovante. Uma futura entidade independente exigirá decisão e
migration, preservando a rastreabilidade já disponibilizada.
