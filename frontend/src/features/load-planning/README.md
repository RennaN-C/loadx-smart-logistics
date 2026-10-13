# Feature: load-planning

Tela de planejamento de carga (OC30). Consome `POST /load-plans`,
`GET /load-plans/{id}`, `POST /load-plans/{id}/approve` e `POST /load-plans/{id}/recalculate`.

## O que existe hoje

- `pages/PlanningPage.tsx` (+ `.css`): monta o plano, mostra o resultado e executa aprovar/recalcular.
- `components/PlanBuilder.tsx`: seleção de caminhão e pedidos.
- `components/PlanSummary.tsx`: métricas do cálculo e as ações.
- `components/PlanItemsTable.tsx`: sequência de carregamento e volumes recusados.
- `components/loadPlanLabels.ts`: rótulos de situação, rotação e motivo de recusa.
- `components/loadPlansErrorMessages.ts`: tradução dos 10 códigos de erro do módulo.
- `api/loadPlansApi.ts`: mapeamento snake_case ↔ camelCase, incluindo a visualização.

## Recuperação de planos (#208)

`CONFIRMADO`: `/planning` abre **Planos existentes**, com resumos paginados do
servidor, situação e ordenação. Query params `page`, `status`, `sort` preservam
consulta na navegação anterior/próxima e após F5. O detalhe permanece em
`/planning/:planId`. O plano salvo é reencontrável após sair para Produtos ou
entrar novamente; clicar no menu nunca calcula nem cria viagem.

`/planning?tab=new` abre o builder existente somente para gestores/ADMIN.
Seleções não calculadas continuam na memória desta tela e se perdem ao sair;
salvar rascunhos exige um contrato separado. O teto de 200 volumes físicos e
validações atuais não mudam. Recálculo cria outro ID e mantém a origem histórica.

`CONFIRMADO`: `PlanHistory` consulta `GET /load-plans` com resumos sem itens.
`PlanContinuity` consulta `GET /load-plans/{id}/continuity` antes de oferecer
criação: vínculos existentes viram links para carregamento/viagem, inclusive
finalizados. Falha de consulta bloqueia criação e oferece retry. Concorrência
continua protegida por lock/constraints no backend; conflito de viagem já
atribuída atualiza os vínculos na tela.

CHECKER vê somente aprovados e pode abrir sessão existente, sem criar ou acessar
viagem. DRIVER não monta a lista nem consulta planos por URL; suas viagens
permanecem no início próprio. Distribuições bloqueadas pela fronteira da OC90
não recebem ações de criação; não há central global nova nesta manutenção.

## Regras que a tela reflete

- **Só caminhão ativo e pedido `READY`** entram na seleção. É regra do backend
  (`MANUAL_ORDER_STATUS_TRANSITIONS` e a checagem de elegibilidade); a tela filtra antes para não
  oferecer o que voltaria erro. Aprovar move os pedidos para `PLANNED`.
- **Plano com volume recusado não pode ser aprovado** (`LOAD_PLAN_HAS_REJECTIONS`). O botão fica
  desabilitado e a tela explica os caminhos: tirar um pedido, usar caminhão maior ou revisar o produto.
- **Caminhão em operação aparece marcado, mas continua selecionável** (OC72). A diferença não é
  estética: `create_load_plan` recusa caminhão INATIVO e só isso — conflito de operação não impede o
  plano. Travar a opção aqui seria o frontend inventando regra que o backend não tem. O aviso vem de
  `GET /trucks/operational-status`, e o conflito **não é calculado nesta tela**.

  Por isso são duas consultas: `GET /trucks` traz as medidas internas, que é o que ajuda a escolher o
  baú, e `operational-status` traz a disponibilidade da OC67 sem medida nenhuma. Caminhão cuja
  situação não chegou aparece sem aviso — esconder a opção tiraria do usuário um caminhão que a API
  aceitaria.
- Os 7 motivos de recusa viram texto que diz o que fazer, não o código cru — é por ele que o usuário
  decide o próximo passo.

## Duas tabelas, não uma

Sequência de carregamento e volumes recusados são leituras diferentes: uma serve a quem carrega o
caminhão, outra a quem resolve pendência. Uma tabela só, com coluna de situação, atrapalharia as duas.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem. `ADMIN` e `LOGISTICS_MANAGER` calculam, aprovam e recalculam.

## Fora de escopo

`CONFIRMADO`: a listagem de planos usa o contrato da #208. A API já implementa
comparação entre caminhões (`OC21`) e explicação por `AIProvider` com fallback
(`OC22`); `loadPlansApi.ts` e a tela atual ainda não consomem essas operações.
A visualização 3D está integrada em `features/load-visualization` (`OC31`).

## Retorno e recuperação (#188)

`CONFIRMADO`: planos persistidos exibem seu link permanente e retorno aos
pedidos, planejamento e início. Volumes aceitos e recusados vinculam à leitura
do pedido em `/orders?order=<id>`. Troca de ID e recálculo assíncrono não
reaproveitam o plano anterior. A recuperação paginada está disponível pela #208;
ver limites no [fluxo operacional](../../../../docs/06-fluxo-operacional.md).


## Pré-validação de volumes físicos — manutenção #204

`CONFIRMADO`: `GET /orders` inclui `volume_count` (soma das quantidades das linhas
visíveis no pedido, sem expor os itens completos). A listagem mostra número de
linhas E de volumes, incluindo a referência curta do pedido para diferenciar
pedidos do mesmo cliente. A seleção resume volumes expandidos e bloqueia o botão
quando o total conhecido excede os 200 volumes permitidos por cálculo síncrono.

O backend permanece fonte de verdade e sempre valida novamente: quando os
resumos estiverem desatualizados, a resposta
`LOAD_PLAN_VOLUME_LIMIT_EXCEEDED` apresenta quantidade real e teto devolvidos
pela API. Cliente não fraciona pedidos automaticamente, não aumenta limites e
não oculta dados faltantes; versões antigas da API exibem contagem desconhecida
e permitem o backend realizar a validação.

Para um único pedido acima de 200 volumes, é necessário revisar as quantidades
no módulo de Pedidos, respeitando a regra de edição em `DRAFT`, ou seguir o
fluxo de planejamento de capacidade maior quando for implementado.
