# Viagens e entregas

`CONFIRMADO`: OC80 acrescenta evidências ao comprovante sem alterar seu schema
ou a conclusão. Contrato API/storage, idempotência, estados e retenção/remoção
estão em [evidences.md](evidences.md). Storage local é opt-in; produção aguarda
política aprovada pela equipe.

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

- Criação exige plano operacional `APPROVED` e motorista elegível. Pedidos
  legados exigem `PLANNED`; partes multi aceitam também `IN_TRANSIT`.
- Viagem usa `SCHEDULED -> IN_ROUTE -> FINISHED`.
- Entrega usa `PENDING -> IN_DELIVERY -> DELIVERED` durante `IN_ROUTE`.
- Início exige confirmação pública de carregamento finalizado e move somente
  pedidos `PLANNED` para `IN_TRANSIT`, sem repetir histórico de outra parte.
- Conclusão registra horário; legado entrega o pedido e multi aguarda todas
  as partes que contêm volumes desse pedido.
- Viagem termina com suas entregas `DELIVERED`; legado exige também pedidos
  `DELIVERED`.
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

`CONFIRMADO`: a arquitetura foi aprovada na revisão do PR #98 e está registrada
na [ADR-024 aceita](../../../../docs/decisions/ADR-024-comprovante-operacional-entrega.md).
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


## OC90 — fluxo multi-caminhão

`CONFIRMADO`: Delivery.distribution_part_id identifica a perna, derivada do plano pelo
servidor; NULL conserva legado. UNIQUE parte/pedido e índice único parcial legado,
FK e triggers de contexto/imutabilidade protegem PostgreSQL (migration 0027).
Trip mantém UNIQUE load_plan_id; retry de criação conserva o conflito público.

Planos atuais de distribuição/parte APPROVED aceitam PLANNED ou IN_TRANSIT na
criação/início. Somente pedidos PLANNED mudam para IN_TRANSIT e recebem histórico.
Conclusão persiste a própria perna sob lock de Order e consulta as partes
necessárias pela reference_service de planejamento e as pernas entregues por SQL.
Somente a última necessária muda Order para DELIVERED. Não bloqueia outra Trip
ou Delivery ao agregar; ordem de locks: Trip → entregas próprias UUID → pedidos/
itens UUID. Leituras após lock renovam objetos e usam READ COMMITTED. A viagem
multi termina pelas suas entregas, independentemente de outras partes.

Comprovante ADR-024 é independente por Delivery e permanece idempotente e
transacional. Falha em B não desfaz A; rollback não publica meia conclusão.
Históricos existentes e vínculos persistidos reconstroem toda a operação.
Permissões efetivas OC112 e recorte do motorista permanecem em vigor, sem novos
papéis ou concessões. Observabilidade ADR-025 não recebe IDs/PII/payload.
ADR-043 registra a proposta estrutural; downgrade falha se existirem entregas
com parte para preservar contexto/auditoria. OC94 permanece fora do escopo.
