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

## O plano vive na URL

**O backend não tem listagem de planos** — só `POST` para criar e `GET /{id}`. Se o resultado ficasse
só no estado do React, recarregar a página perderia o plano sem nenhuma forma de recuperá-lo. Por isso
a rota é `/planning/:planId`, e a página carrega pelo id.

Recalcular gera um plano **novo**, com id diferente. Nesse caso a página apenas navega para o id novo
e deixa o efeito carregar — não existem duas fontes de verdade para o mesmo plano na tela.

## Regras que a tela reflete

- **Só caminhão ativo e pedido `READY`** entram na seleção. É regra do backend
  (`MANUAL_ORDER_STATUS_TRANSITIONS` e a checagem de elegibilidade); a tela filtra antes para não
  oferecer o que voltaria erro. Aprovar move os pedidos para `PLANNED`.
- **Plano com volume recusado não pode ser aprovado** (`LOAD_PLAN_HAS_REJECTIONS`). O botão fica
  desabilitado e a tela explica os caminhos: tirar um pedido, usar caminhão maior ou revisar o produto.
- Os 7 motivos de recusa viram texto que diz o que fazer, não o código cru — é por ele que o usuário
  decide o próximo passo.

## Duas tabelas, não uma

Sequência de carregamento e volumes recusados são leituras diferentes: uma serve a quem carrega o
caminhão, outra a quem resolve pendência. Uma tabela só, com coluna de situação, atrapalharia as duas.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem. Só `LOGISTICS_MANAGER` calcula, aprova e recalcula.

## Fora de escopo

Listagem/histórico de planos (não existe rota) e comparação entre caminhões (`OC21`, backend).
A visualização 3D é a `OC31`, em `features/load-visualization`.
