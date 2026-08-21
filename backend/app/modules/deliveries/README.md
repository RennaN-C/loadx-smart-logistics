# Viagens e entregas

Viagem, entregas, estados e histórico. Roteirização externa não entra no MVP.

## Estrutura implementada

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.

## Endpoints

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
- Mudanças do agregado, pedidos e histórico usam um único commit ou rollback.
- `LOGISTICS_MANAGER` cria e opera; `ADMIN` consulta; `DRIVER` consulta e opera
  somente viagem própria com vínculo e motorista ativos; `CHECKER` é negado.

## Pendências

- `PENDENTE DE DEFINIÇÃO`: o módulo `loading` precisa materializar o estado
  finalizado para liberar o início real da viagem.
- `PENDENTE DE DEFINIÇÃO`: estados de exceção, cancelamento, reentrega e
  ocorrências exigem decisão e implementação futuras.
