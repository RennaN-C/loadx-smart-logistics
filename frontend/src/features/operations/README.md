# Feature: operations

Painel operacional da v1.1.0 (OC74), integrado à Visão geral `/` pela manutenção #206. Consome
`GET /operational-indicators` (OC69).

## O que existe hoje

- `pages/OperationsDashboardPage.tsx` (+ `.css`): componente reutilizado na Visão geral, com os quatro
  grupos de indicadores, carregando, erro, nova tentativa e atualização.
- `api/operationalIndicatorsApi.ts`: mapeamento snake_case para camelCase.
- `types.ts`: o contrato da OC69.

## Nada é calculado aqui

`CONFIRMADO`: todo número vem do backend, que o apura em tempo de leitura. A tela
não soma, não divide e **não deriva porcentagem**.

Não é preciosismo: a OC69 deixou taxas, percentuais, médias e séries históricas
de fora de propósito, por não existir contrato de dados uniforme para eles nesta
versão. "4 de 6 disponíveis" vira "67% da frota livre" com uma linha de código —
e aí a tela passa a publicar uma métrica que o domínio não sustenta, que é
exatamente o que a OC74 põe fora de escopo. Há teste que falha se um `%`
aparecer na tela.

`CONFIRMADO` (UI05): barras segmentadas representam diretamente as contagens de
status de viagens e entregas, acompanhadas dos valores absolutos. Elas não
publicam percentual, tendência ou série histórica derivada.

## O período faz parte do número

Cada grupo mostra o `period` que a API devolveu: a frota é `CURRENT_SNAPSHOT`
(retrato de agora), viagens, entregas e ocorrências são `ALL_TIME` (tudo o que
já houve). "2 em rota" sem esse recorte não quer dizer nada.

A tradução vive num mapa, não num `if`: período novo que a tela ainda não
conheça aparece **cru**, em vez de ser traduzido por chute.

## Por que não é uma aba de `/reports`

As duas telas mostram número, mas com contratos de confiança diferentes.
`/reports` apura PEDIDOS somando no cliente, e avisa na própria tela que lê no
máximo 1000 por vez. Esta só exibe o que o servidor apurou. Juntá-las numa aba
só borraria justamente a distinção que a OC74 cobra — "todos os números exibidos
vêm da OC69".

## Permissões

`CONFIRMADO`: `GET /operational-indicators` responde a `ADMIN` e
`LOGISTICS_MANAGER`. `CHECKER` e `DRIVER` não acessam o painel global, e o bloco global não é montado para eles. O item separado foi removido do menu;
`/operations` preserva acesso legado com guarda e redirecionamento para `/`.

O motivo não é dado pessoal — é **alcance**: conferente e motorista enxergam a
própria tarefa, não a operação inteira. Por isso `AppLayout` usa uma constante
própria (`OPERATION_OVERVIEW_READERS`) em vez de reaproveitar
`PERSONAL_DATA_READERS`, que tem os mesmos perfis por outra razão.

## Base vazia

Base sem dados responde `200` com todos os contadores em zero. A tela mostra os
zeros; não é erro e não vira estado vazio.

## Fora de escopo

Filtro por período, gráfico de série histórica, métrica financeira e qualquer
taxa derivada. Nenhum tem suporte na OC69 desta versão.

## Integração na Visão geral — #206

`CONFIRMADO`: o modo incorporado usa a mesma chamada e grupos, destacando
indicadores prioritários e mantendo os demais em detalhes expansíveis. Períodos,
zeros, falhas, nova tentativa e atualização manual continuam funcionando. Não
consulta séries históricas nem calcula porcentagens. O contrato independente de
`/reports` continua distinto: aquela página apura somente pedidos, com teto.

## Gráficos operacionais — 25/10/2026

`CONFIRMADO`: a Visão geral e o painel operacional apresentam anel de viagens
e colunas de entregas usando exatamente totais/estados/períodos da OC69.
Ângulos e alturas são escalas de desenho, sem publicar métricas derivadas.
Zeros e falhas preservam o comportamento anterior. Gráficos não simulam evolução
semanal nem alteram a autorização do endpoint.
