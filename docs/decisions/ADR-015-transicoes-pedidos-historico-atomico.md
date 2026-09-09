# ADR-015: transições de pedidos e histórico atômico

Status: aceita

## Contexto

A OC52 precisa impedir saltos arbitrários de estado, bloquear alterações em
pedidos já liberados para operação e garantir que pedido e histórico nunca sejam
confirmados separadamente. A aprovação de planos já aplica esse padrão para
`READY -> PLANNED`, mas o `PATCH` genérico de pedidos ainda aceita atribuição
direta de qualquer estado conhecido.

## Decisão

- As transições manuais do `LOGISTICS_MANAGER` são `DRAFT -> READY`,
  `DRAFT -> CANCELED`, `READY -> DRAFT` e `READY -> CANCELED`.
- `READY -> PLANNED` pertence exclusivamente à aprovação de plano;
  `PLANNED -> IN_TRANSIT` pertence ao início de viagem; e
  `IN_TRANSIT -> DELIVERED` pertence à conclusão de entrega.
- `DELIVERED` e `CANCELED` são terminais. Transições não listadas são rejeitadas.
- Somente `DRAFT` aceita edição de dados. `READY` deve voltar explicitamente a
  `DRAFT`; estados posteriores são imutáveis. Itens referenciados por plano
  continuam imutáveis conforme a ADR-014.
- O status sai do `PATCH` genérico e passa a caso de uso HTTP explícito.
- O service dono bloqueia a entidade e confirma entidade e histórico em um único
  commit. O histórico composto usa `stage_status_change` e `flush`.
- Ações manuais usam o UUID do usuário autenticado. Eventos automáticos podem
  usar `changed_by = null`, sem usuário artificial de sistema.
- A criação registra `null -> DRAFT`. Repetir o estado atual é idempotente e não
  cria outro histórico.

## Consequências

- A OC52 altera intencionalmente o contrato de atualização de pedidos e exige
  atualização simultânea de OpenAPI, testes e consumidores frontend futuros.
- Falha de histórico reverte também a criação ou transição do pedido.
- O padrão transacional passa a ser reutilizável em carregamento, viagens e
  entregas, sem antecipar as decisões D07, D08, D09 e D10.
- Cancelamento de pedido `PLANNED` permanece bloqueado até existir fluxo aprovado
  para invalidar ou substituir um plano aprovado.
