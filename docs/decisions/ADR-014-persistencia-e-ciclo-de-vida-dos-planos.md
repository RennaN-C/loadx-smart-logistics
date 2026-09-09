# ADR-014: persistência e ciclo de vida dos planos

Status: aceita

## Contexto

A integração da OC20 precisa persistir resultados individuais, preservar o
resultado histórico diante de alterações cadastrais e executar criação,
aprovação e recálculo com transações coerentes.

## Decisão

- Não existe tabela `volumes`. Cada unidade expandida é persistida em
  `load_plan_items` com identidade `(order_item_id, volume_index)`, e o índice é
  iniciado em `1`.
- `load_plans`, `load_plan_orders` e `load_plan_items` mantêm FKs de proveniência.
  O plano também guarda snapshots do caminhão, produto e item de pedido usados no
  cálculo.
- FKs compostas garantem que cada volume pertença a um pedido associado ao plano
  e que `order_item_id`, `order_id` e `product_id` descrevam a mesma origem.
- Itens de pedido referenciados por qualquer plano não podem ser substituídos. A
  FK usa restrição de exclusão; o service de pedidos serializa a alteração por
  lock e consulta a interface pública de referências do planejamento antes da
  tentativa.
- Os únicos estados persistidos são `CALCULATED`, `APPROVED` e `REJECTED`, em
  `VARCHAR` protegido por `CHECK`.
- `SUPOSIÇÃO TÉCNICA`: resultado sem nenhum volume colocado é `REJECTED`;
  resultado com ao menos um colocado é `CALCULATED`, inclusive quando parcial.
  A suposição dá uso objetivo ao estado aprovado sem converter uma rejeição
  individual em falha transacional.
- Criação comum aceita apenas caminhão ativo e pedidos distintos em `READY`.
  O limite síncrono é 200 volumes expandidos.
- Somente `CALCULATED` sem volumes rejeitados pode virar `APPROVED`. A aprovação
  e a mudança dos pedidos para `PLANNED` ocorrem no mesmo commit, junto de seus
  registros de histórico.
- Recálculo sempre cria outro plano, aponta diretamente para a origem por
  `recalculated_from_id`, recarrega os dados atuais, grava novos snapshots e não
  altera o plano anterior.
- `SUPOSIÇÃO TÉCNICA`: como a aprovação já deixa os pedidos em `PLANNED`, o
  recálculo aceita `READY` ou `PLANNED` somente para o conjunto exato herdado do
  plano de origem. A criação comum continua proibida para pedidos `PLANNED`.
- A aprovação de um plano recalculado mantém `PLANNED` de forma idempotente. O
  plano aprovado anterior permanece histórico e imutável.
- Criação, aprovação e recálculo são exclusivas de `LOGISTICS_MANAGER`. `ADMIN`
  e `LOGISTICS_MANAGER` consultam qualquer plano; `CHECKER` consulta somente
  plano `APPROVED`; `DRIVER` permanece negado enquanto não houver vínculo
  operacional aprovado.

## Consequências

- Atualizações futuras de produto ou caminhão não reescrevem um resultado já
  calculado; um recálculo evidencia a nova fotografia por outro registro.
- Plano parcial pode ser inspecionado, mas não aprovado.
- `RISCO IDENTIFICADO`: sem estado de substituição ou ponteiro de versão ativa,
  mais de um plano histórico pode permanecer `APPROVED`; consumidores futuros
  devem definir qual descendente alimenta a operação sem mutar os anteriores.
- Models e migration precisam de revisão do responsável por banco; contrato HTTP
  precisa de revisão do responsável pelo frontend. A explicação por IA permanece
  desacoplada para a OC22 e para o responsável por integrações.
