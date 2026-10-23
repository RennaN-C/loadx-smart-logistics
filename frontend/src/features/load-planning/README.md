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
servidor, situação e ordenação. Clicar na placa filtra o caminhão no servidor, com ação para limpar o filtro.
Query params `page`, `status`, `sort`, `truck` preservam
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
permanecem no início próprio. Cada parte de uma distribuição totalmente aprovada
consulta agora a continuidade real da OC90; partes históricas ou distribuição
incompleta continuam bloqueadas pelo backend. Não há central global nova.

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

## OC89 — seleção automática e distribuição persistida

`CONFIRMADO`: Novo planejamento oferece **Um caminhão** (fluxo legado preservado)
e **Seleção automática da frota**. A ação `Otimizar e salvar distribuição` envia
somente `order_ids` a `POST /load-distributions/optimize`; HTTP 201 já representa
uma proposta persistida, completa, de 1–10 caminhões e até 200 volumes físicos.
Não há packing, disponibilidade, seleção de frota ou divisão de volumes no cliente.

`CONFIRMADO`: `distributionsApi.ts` centraliza DTOs e conversões dos contratos
OC87/88. A consulta estável é `/planning/distributions/:distributionId?part=:partId`.
Os resumos de Planos existentes usam `distribution_id` (inclusive em versões
históricas) para abrir o agregado. Consultar, F5, alternar veículos ou voltar de
Produtos nunca chama optimize. O detalhe legado oferece retorno à distribuição e
oculta aprovação/recálculo individuais quando existe esse vínculo. A listagem
continua mostrando planos/versões, portanto várias linhas podem abrir a mesma
necessidade; não se trata de distribuições duplicadas.

`CONFIRMADO`: cartões apresentam placa/modelo do snapshot histórico, métricas e
estado de cada parte; a seleção atualiza tabela e cena exclusivamente pelo
`load_plan.id`. O viewer é lazy e recebe `key` do plano, descartando a cena anterior
antes da nova consulta. A tabela mostra índice original/quantidade e item de origem.
Erros da cena permitem repetir somente a leitura. Coordenadas não são alteradas.

`CONFIRMADO`: aprovação/cancelamento usam o agregado; cancelar uma parte exige
confirmação e deixa a necessidade incompleta. Reprocessamento consulta preflight,
escolhe um caminhão elegível e envia `expected_load_plan_id`; não redistribui volumes
entre partes. Erro mantém a proposta e exige atualizar o agregado antes de outra
ação. Cliques concorrentes são bloqueados por estado e ref síncrona. Falha ambígua
de rede na otimização orienta consultar Planos existentes antes de repetir; a API
não fornece chave de idempotência para criação, e o frontend não inventa uma.

`CONFIRMADO`: UI segue `loadx.planning.read/create/approve`, sem ampliar permissões.
ADMIN/gestor de sistema gerenciam; CHECKER lê aprovados; DRIVER não consulta.
Perfis flexíveis seguem o catálogo atual. Aprovação parcial não libera operação;
com vários caminhões, carregamento/viagens permanecem na fronteira da OC90. Uma
parte completa e aprovada reutiliza a continuidade real já existente.

`CONFIRMADO`: aparência utiliza tokens existentes, controles nativos, foco visível,
feedback real e grade responsiva. Evidências Chromium em
[docs/evidencias/oc89](../../../../docs/evidencias/oc89/README.md).
`RISCO IDENTIFICADO`: o backend não publica prova de otimalidade nem justificativa
individual por alternativa descartada; a interface descreve a estratégia heurística
documentada e a solução salva, sem inventar por que um caminhão específico falhou.
Rascunhos não calculados continuam locais à tela, sem localStorage.


## Recuperação idempotente (#254)

`CONFIRMADO`: seleção automática usa Idempotency-Key UUID e permite consultar
resultado no servidor ou repetir a mesma solicitação após falha/F5.
SessionStorage contém apenas ator/chave/seleção da aba, não plano, token nem
prova de persistência. Nenhum POST ocorre na montagem. Falha de storage mantém
chave em memória; fechar aba/perder storage exige consultar Planos existentes.
Contrato e limites: ADR-047. A performance da PR #262 permanece independente.

## Plano e operação separados — #255

`CONFIRMADO`: a listagem separa “Plano: aprovado” da situação logística real.
Usuários com leitura de viagens, pedidos e carregamento recebem filtros
Em andamento / Concluídos / Todos (`scope` na URL, restaurado após F5) e resumo
SQL paginado. Em andamento inclui preparações ainda sem operação; conclusão
requer viagem finalizada e todos os pedidos entregues em todas as partes.
Viagem interrompida/cancelada é retomável por link, sem oferecer outra criação.
Pedidos fora de READY desabilitam aprovação/recálculo do cálculo histórico com
explicação; a decisão permanece validada transacionalmente pelo servidor.
