# OC109 — Evidências de fila e reprocessamento

`CONFIRMADO`: Chromium headless, API real e PostgreSQL 16 local, em banco isolado
`loadx_oc109_browser`, com dados exclusivamente fictícios. Nenhum deploy, acesso
ou modificação de main/pentest-lab/OC98/OC90. Imagens capturadas do navegador sem
edição; os contadores correspondem a cada instante do cenário.

## Interface

| Largura | Fila claro / escuro | Detalhe claro / escuro |
|---|---|---|
| 375 | [Claro](fila-light-375.png) / [Escuro](fila-dark-375.png) | [Claro](detalhe-light-375.png) / [Escuro](detalhe-dark-375.png) |
| 768 | [Claro](fila-light-768.png) / [Escuro](fila-dark-768.png) | [Claro](detalhe-light-768.png) / [Escuro](detalhe-dark-768.png) |
| 1280 | [Claro](fila-light-1280.png) / [Escuro](fila-dark-1280.png) | [Claro](detalhe-light-1280.png) / [Escuro](detalhe-dark-1280.png) |
| 1920 | [Claro](fila-light-1920.png) / [Escuro](fila-dark-1920.png) | [Claro](detalhe-light-1920.png) / [Escuro](detalhe-dark-1920.png) |

Confirmação: [375 claro](confirmacao-light-375.png), [375 escuro](confirmacao-dark-375.png),
[1280 claro](confirmacao-light-1280.png), [1280 escuro](confirmacao-dark-1280.png).
Estados reais: [vazio por filtros](vazio-light-375.png),
[falha de transporte](erro-dark-375.png), [concluído após worker](concluido-dark-375.png).
Total: **23 PNGs**.

`CONFIRMADO`: revisão visual de fila/detalhe/confirmação, incluindo tablet e
celular; corrigidos sobreposição do cabeçalho sobre o modal e botões quebrando
palavras no tablet. Uma navegação de Configurações, componentes/modal existentes,
tokens claro/escuro/automático, sem dependências novas.

[validacao-visual.json](validacao-visual.json): oito combinações de tema/largura,
sem overflow na página ou diálogo, foco dentro do modal e nenhum erro JavaScript.
[validacao-estados.json](validacao-estados.json): vazio com filtros reais, bloqueio
de transporte e retry recuperado, Automático acompanhando claro/escuro em tempo
real, árvore de acessibilidade sem controles interativos visíveis sem nome.
Vitest cobre Escape/restauração de foco, confirmação, falha de comando com UUID
estável, paginação, filtros e negação 401/403 sem conservar dados.

## Fluxo persistente

[validacao-fluxo.json](validacao-fluxo.json) registra a operação real:

1. ADMIN confirma reprocessamento de evento com falha do mock.
2. Evento fica PENDING; abrir a mesma URL após recarga reconsulta e restaura o detalhe.
3. Worker independente confirma SUCCEEDED; recarga mostra Concluído, duas tentativas
   e nenhuma ação de reprocessamento para o sucesso.
4. Replay HTTP do **mesmo comando** retorna 200/SUCCEEDED, sem reabrir o evento.
   Token CSRF incompatível foi recusado com 403.
5. Abertura da origem navega para a viagem já existente, mediante autorização da API.
6. Contador pessoal permanece **6 → 6**, independente do resultado externo simulado.

As falhas do transporte foram injetadas somente no adapter do cenário local,
antes de executar o worker, para produzir tentativas persistentes reais. A
aplicação consultou os contratos reais; nenhum fetch foi substituído por dados
artificiais na interface. O worker de produção desta OC só seleciona o mock.

## Banco, testes e benchmark

`CONFIRMADO`: migrations heads/current/upgrade/check/downgrade/upgrade em outro
banco isolado vazio. Head único `20261020_0027`, anterior `20261020_0026`. Testes
PostgreSQL verificam também recusa de downgrade com histórico, backfill de cada
estado legado sem envio e preservação de fatos/destinatários/leitura.

Regressões executadas: OC84/OC103/fila (91 testes), política/backfill/comandos e
paginação (67 testes), fila/OpenAPI/migrations após correção de concorrência (55),
contratos/política/readiness/head (46). Suíte frontend completa: **944 testes em
107 arquivos**; lint, TypeScript/build, bundle budget e npm audit sem vulnerabilidades.
Resultados da suíte backend completa com cobertura, CI, Trivy e Sonar são registrados
no corpo/checks da [PR #230](https://github.com/RennaN-C/loadx-smart-logistics/pull/230),
atualizados para o SHA final; estes grupos focados se sobrepõem e não devem ser somados.

[benchmark.json](benchmark.json): 20 fatos gerados pelo service de ocorrências,
20 execuções reais de claim/commit/mock/confirmação e 30 consultas paginadas de
20 eventos sobre 35 registros. Mediana worker **15,88 ms**, p95 **21,74 ms**;
mediana listagem **4,12 ms**, p95 **6,49 ms**. PostgreSQL local, sem latência externa;
não representa SLA/capacidade de produção. A inicialização real por
`python -m app.modules.notifications.worker` e encerramento SIGTERM também foram
executados com saída 0; o teste unitário cobre espera, erro de banco e dispose.

## Limites operacionais

`RISCO IDENTIFICADO`: exige provisionar worker e coordenar corte de escritores
com migration antes de implantação. Não há envio externo real, webhook de saída
aprovado, promessa exactly-once, retenção automática ou alerta externo.
Lease expirado/timeout exige revisão explícita; o mock admite reprocessamento
confirmado, sem alterar estado terminal legado ou a caixa pessoal. Ver ADR-043
e notifications/README para política e inicialização proposta no Render.
