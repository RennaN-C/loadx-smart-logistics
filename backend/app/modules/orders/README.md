# Pedidos

Pedido, itens, prioridade, destino, sequência de entrega e ciclo de status.

## Estrutura

- `models.py`: entidades SQLAlchemy `Order` e `OrderItem`.
- `schemas.py`: contratos Pydantic `OrderCreate`, `OrderUpdate`,
  `OrderStatusChange`, `OrderRead`, `OrderItemCreate` e `OrderItemRead`.
- `repository.py`: consultas e persistência de pedidos com seus itens.
- `service.py`: regras de criação, consulta, atualização, transição de status e
  validação de vínculos.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `GET /api/v1/orders`: lista pedidos com itens.
- `POST /api/v1/orders`: cria pedido.
- `GET /api/v1/orders/{id}`: consulta pedido por ID.
- `PATCH /api/v1/orders/{id}`: atualiza campos enviados.
- `PATCH /api/v1/orders/{id}/status`: executa uma transição manual de status.

`CONFIRMADO`: `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem consultar. Somente
`LOGISTICS_MANAGER` pode criar, atualizar ou executar transições manuais.
`DRIVER` não acessa o módulo enquanto não existir vínculo aprovado com seus
pedidos.

## Regras implementadas

- Pedido criado começa com `status = "DRAFT"`.
- A criação grava atomicamente o histórico inicial `null -> DRAFT` com o usuário
  responsável.
- Pedido deve possuir cliente existente e pelo menos um item.
- Cada item deve possuir produto existente.
- `quantity` e `delivery_sequence` devem ser maiores que zero.
- `priority` é normalizado para maiúsculas.
- `expected_delivery_at` deve vir com timezone e é normalizado para UTC.
- O `PATCH` genérico não aceita `status` e só edita pedidos em `DRAFT`.
- `items`, quando enviado no `PATCH`, substitui o conjunto somente enquanto seus
  itens ainda não forem referenciados por um plano de carga.
- As transições manuais permitidas são `DRAFT -> READY`, `DRAFT -> CANCELED`,
  `READY -> DRAFT` e `READY -> CANCELED`.
- `READY -> PLANNED` pertence exclusivamente à aprovação do plano de carga.
- Repetir o status atual é idempotente e não duplica o histórico.
- Cada transição efetiva e seu histórico usam uma única transação com commit ou
  rollback conjunto.
- `ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN` retorna `409` quando a substituição
  apagaria a proveniência histórica de `load_plan_items`.
- Todas as rotas exigem autenticação Bearer e consultam o papel e o estado atual
  do usuário no banco.

`CONFIRMADO`: estas regras foram aprovadas em D04 e D05 e registradas na ADR-015.
