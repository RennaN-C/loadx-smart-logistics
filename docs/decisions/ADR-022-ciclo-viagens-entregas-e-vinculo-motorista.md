# ADR-022: ciclo de viagens, entregas e vínculo do motorista

Status: aceita

## Contexto

A `OC09` precisa ligar planos aprovados, carregamento, motoristas, pedidos,
viagens, entregas e histórico sem duplicar o caminhão persistido no plano. As
decisões `D07` a `D10` ainda não definiam a máquina de estados, o tratamento de
entregas problemáticas, a fronteira com o módulo de carregamento nem o catálogo
de entidades auditáveis. Também faltava uma relação segura entre a identidade
autenticada `User` e o cadastro operacional `Driver`.

O MVP precisa entregar o caminho operacional principal sem antecipar fluxos de
reentrega, cancelamento ou tratamento de ocorrências que ainda não possuem
contrato aprovado.

## Alternativas consideradas

- Persistir `truck_id` também em `trips`: descartada porque o caminhão já é
  determinado por `load_plan_id` e a duplicação permitiria divergência.
- Usar `drivers.user_id`: descartada porque faria o cadastro operacional,
  administrado pelo responsável logístico, controlar um vínculo de identidade.
- Criar tabela de associação `users_drivers`: descartada porque a cardinalidade
  aprovada é 1:1 e a tabela adicionaria complexidade sem benefício no MVP.
- Manter todos os estados de exceção previstos inicialmente: descartada porque
  cancelamento, falha, ausência e reentrega exigem regras comerciais e
  integração com ocorrências ainda não aprovadas.
- Liberar a viagem apenas com plano aprovado: descartada porque aprovação do
  planejamento e finalização física do carregamento são fatos diferentes.

## Decisão

- `Trip` mantém somente `load_plan_id`, `driver_id`, `status`, `started_at` e
  `finished_at`. O caminhão é obtido exclusivamente pelo plano de carga.
- Os estados da viagem na `OC09` são `SCHEDULED`, `IN_ROUTE` e `FINISHED`, com
  transições `SCHEDULED -> IN_ROUTE -> FINISHED`.
- Os estados da entrega são `PENDING`, `IN_DELIVERY` e `DELIVERED`, com
  transições `PENDING -> IN_DELIVERY -> DELIVERED`.
- Repetir o estado atual é idempotente e não cria histórico. Qualquer salto ou
  retorno é rejeitado.
- `started_at`, `delivered_at` e `finished_at` são registrados em UTC nas
  respectivas transições. Constraints mantêm status e horários coerentes.
- A viagem pode ser criada para um plano `APPROVED` e motorista ativo, mas só
  entra em `IN_ROUTE` quando o módulo dono confirmar carregamento `FINISHED`.
  Enquanto loading não possuir persistência, sua interface pública falha
  fechada e mantém essa transição bloqueada.
- O início da viagem altera todos os pedidos vinculados de `PLANNED` para
  `IN_TRANSIT`. A conclusão de cada entrega altera seu pedido de `IN_TRANSIT`
  para `DELIVERED`.
- A viagem só termina quando todas as entregas estão `DELIVERED`. Estados de
  exceção e finalização parcial ficam fora da `OC09`; ocorrências adicionam
  contexto sem substituir status.
- Cada pedido do plano produz uma entrega. Todos os itens de um pedido devem
  declarar a mesma `delivery_sequence`. Os pedidos são ordenados por
  `(delivery_sequence, order_id)` e recebem `Delivery.sequence` contígua e
  1-based. Assim, empates permanecem determinísticos e a sequência final é
  única dentro da viagem.
- Um pedido participa de no máximo uma entrega no MVP. As FKs usam exclusão
  restrita e constraints únicas protegem plano, pedido e sequência contra
  concorrência.
- O catálogo interno de `status_history.entity_type` é fechado em `ORDER`,
  `LOAD_PLAN`, `TRIP` e `DELIVERY`. Não existe endpoint público de histórico na
  `OC09`.
- O vínculo de identidade fica em `users.driver_id`, anulável, único e com FK
  restritiva para `drivers.id`. Somente `ADMIN` administra o vínculo. Um usuário
  pode ter papel `DRIVER` sem vínculo, mas nesse caso continua sem acesso
  operacional. Um vínculo preenchido exige papel `DRIVER` e motorista existente.
- Mudança de vínculo revoga as sessões do usuário. Acesso operacional exige
  usuário e motorista ativos e correspondência exata entre `users.driver_id` e
  `trips.driver_id`.
- `LOGISTICS_MANAGER` cria viagens e executa qualquer transição aprovada.
  `ADMIN` consulta qualquer viagem. `DRIVER` consulta e altera somente a própria
  viagem e suas entregas. `CHECKER` não acessa viagens ou entregas.
- Trip, Delivery, pedidos relacionados e todos os históricos da operação usam
  um único commit. Qualquer falha causa rollback integral.

## Consequências

- A `OC09` entrega persistência, criação, consulta e regras operacionais sem
  duplicar caminhão nem adicionar `observation` a `Delivery`.
- O caminho positivo de início da viagem continua dependente do módulo loading;
  a dependência fica explícita e testável sem implementar o módulo de outro
  desenvolvedor.
- Cancelamento, falha, ausência, recusa e reentrega exigirão nova decisão e nova
  migration caso sejam incorporados ao MVP.
- A FK em `users` mantém o vínculo sob administração de identidade e torna a
  autorização por objeto simples e indexável.
- O histórico passa a rejeitar tipos arbitrários tanto no schema quanto no
  PostgreSQL.
