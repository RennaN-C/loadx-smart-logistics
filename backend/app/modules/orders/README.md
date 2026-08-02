# Pedidos

Pedido, itens, prioridade, destino e sequência de entrega.

## Estrutura

- `models.py`: entidades SQLAlchemy `Order` e `OrderItem`.
- `schemas.py`: contratos Pydantic `OrderCreate`, `OrderUpdate`, `OrderRead`, `OrderItemCreate` e `OrderItemRead`.
- `repository.py`: consultas e persistência de pedidos com seus itens.
- `service.py`: regras de criação, consulta, atualização e validação de vínculos.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `GET /api/v1/orders`: lista pedidos com itens.
- `POST /api/v1/orders`: cria pedido.
- `GET /api/v1/orders/{id}`: consulta pedido por ID.
- `PATCH /api/v1/orders/{id}`: atualiza campos enviados.

`CONFIRMADO`: `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem consultar. Somente `LOGISTICS_MANAGER` pode criar ou atualizar. `DRIVER` não acessa o módulo enquanto não existir vínculo aprovado com seus pedidos.

## Regras implementadas

- Pedido criado começa com `status = "DRAFT"`.
- Pedido deve possuir cliente existente.
- Pedido deve possuir pelo menos um item.
- Cada item deve possuir produto existente.
- `quantity` e `delivery_sequence` devem ser maiores que zero.
- `priority` é normalizado para maiúsculas.
- `expected_delivery_at` deve vir com timezone e é normalizado para UTC.
- `items`, quando enviado no `PATCH`, substitui o conjunto de itens do pedido.
- Todas as rotas exigem autenticação Bearer e consultam o papel e o estado atual do usuário no banco.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: fluxo final de transição de status por perfil.
- `PENDENTE DE DEFINIÇÃO`: regra de bloqueio para edição de pedidos já planejados ou em viagem.
