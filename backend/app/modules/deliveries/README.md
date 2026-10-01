# Viagens e entregas

Viagem, entregas, estados e histórico. Roteirização externa não entra no MVP.

## Estrutura implementada

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.

## Endpoints

- `GET /api/v1/trips`: lista viagens com paginação e resumo sem PII.
- `POST /api/v1/trips`: cria viagem e uma entrega por pedido do plano.
- `GET /api/v1/trips/{id}`: consulta viagem com entregas.
- `PATCH /api/v1/trips/{id}/status`: avança a viagem.
- `PATCH /api/v1/deliveries/{id}/status`: avança uma entrega.

## Regras implementadas

- Criação exige plano `APPROVED`, motorista ativo e pedidos `PLANNED`.
- Viagem usa `SCHEDULED -> IN_ROUTE -> FINISHED`.
- Entrega usa `PENDING -> IN_DELIVERY -> DELIVERED` durante `IN_ROUTE`.
- Início exige confirmação pública de carregamento finalizado e move todos os
  pedidos para `IN_TRANSIT`.
- Conclusão da entrega registra horário e move o pedido para `DELIVERED`.
- Viagem termina somente com todas as entregas e pedidos `DELIVERED`.
- Repetir o estado atual é idempotente.
- A transição efetiva `SCHEDULED -> IN_ROUTE` pelo endpoint HTTP envia depois do
  commit uma notificação mock ao motorista; repetição idempotente não duplica o
  aviso.
- Mudanças do agregado, pedidos e histórico usam um único commit ou rollback.
- `LOGISTICS_MANAGER` cria e opera; `ADMIN` consulta; `DRIVER` consulta e opera
  somente viagem própria com vínculo e motorista ativos; `CHECKER` é negado.
- A listagem usa `page`, `page_size` e `sort_order`, ordena por `created_at` e
  `id` na mesma direção e retorna `delivery_count` sem carregar dados pessoais.
- `ADMIN` e `LOGISTICS_MANAGER` listam todas as viagens; `DRIVER` lista somente
  as vinculadas ao próprio `users.driver_id` e falha fechado sem vínculo ou com
  motorista inativo.

## OC78 — comprovante operacional

`CONFIRMADO`: a implementação da branch reutiliza `Delivery.delivered_at` e
o único histórico da conclusão `IN_DELIVERY -> DELIVERED`. Não há tabela ou
migration nova. Dados mínimos: `id` do histórico, `delivery_id`, `trip_id`,
`order_id`, `driver_id`, `delivered_at`, `recorded_at` e `recorded_by`.

- `POST /api/v1/deliveries/{id}/receipt`, corpo `{}` obrigatório: reutiliza a
  conclusão existente e devolve `200 DeliveryReceiptRead`.
- `GET /api/v1/deliveries/{id}/receipt`: consulta o comprovante, inclusive quando
  a entrega foi concluída pelo endpoint de status anterior.

`CONFIRMADO`: a conclusão continua restrita a `IN_DELIVERY` durante `IN_ROUTE`.
Repetição autorizada mantém o mesmo histórico, horário e responsável, inclusive
após viagem `FINISHED`. O schema rejeita campos extras; os vínculos, horários e
usuário são obtidos do servidor. Gestor opera/consulta; administrador consulta;
motorista ativo/vinculado acessa somente a própria viagem; conferente é negado.
Sessão, Origin e CSRF mantêm as proteções existentes.

`CONFIRMADO`: entrega, pedido e históricos compartilham commit/rollback. A
projeção é montada antes do commit; dados sob bloqueio são atualizados para
serializar tentativas concorrentes, inclusive com entidades já no identity map.
Histórico ausente, duplicado ou sem responsável falha fechado com
`DELIVERY_RECEIPT_HISTORY_INVALID`; consulta antes de concluir usa
`DELIVERY_RECEIPT_NOT_AVAILABLE`. Não há backfill ou responsável fictício.

`PENDENTE DE DEFINIÇÃO`: alinhamento/revisão de Rennan antes da integração,
conforme [ADR-024 proposta](../../../../docs/decisions/ADR-024-comprovante-operacional-entrega.md).
Recebedor, correções, foto, assinatura, geolocalização, upload/storage e retenção
externa ficam fora desta versão. Não há campos ou referências mock de evidência.

Testes específicos (em `backend`, integração com `TEST_DATABASE_URL` exclusivo):

```powershell
python -m pytest -q tests/unit/test_delivery_service.py tests/integration/test_delivery_receipts_api.py tests/integration/test_delivery_receipt_concurrency.py tests/integration/test_deliveries_api.py tests/e2e/test_complete_flow.py
```

## Pendências

- `PENDENTE DE DEFINIÇÃO`: estados de exceção, cancelamento e reentrega exigem
  decisão e implementação futuras. Ocorrências já são persistidas pelo módulo
  dono e adicionam contexto sem substituir o status operacional.

## OC65 — reserva do motorista

`CONFIRMADO`: criação e início efetivo usam a validação pública de
`DriverService`; o início exclui a própria viagem. A reserva dura de `SCHEDULED`
até o commit de `FINISHED`. Repetição idempotente e conclusão mantêm seu fluxo.
`DeliveryReferenceService` expõe a consulta de viagens ativas através do
repository dono, também reutilizada pela identificação de viagem no WhatsApp.
Conflito retorna HTTP `409 DRIVER_OPERATION_CONFLICT` (ver `docs/05`).
