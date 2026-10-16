# OC107 — Evidências visuais

`CONFIRMADO`: Chromium headless, API FastAPI e PostgreSQL 16 locais reais em
banco isolado, conta ADMIN e dados fictícios. Não foram interceptadas respostas
da busca. Oito capturas `busca-<375|768|1280|1920>-<light|dark>.png` mostram o
cabeçalho/painel no tema do sistema; sem overflow horizontal ou erro JavaScript.
A barra de rolagem limita sugestões extensas no painel; textos quebram no mobile.

`CONFIRMADO`: `resultados.json` registra abertura do cadastro por listagem
filtrada, F5 preservando filtro, Enter abrindo detalhe de pedido, retorno do
navegador e Escape. A validação de vínculo DRIVER e RBAC dos quatro perfis está
nos testes PostgreSQL e de componente, sem afirmar sessão real desses perfis no
Chromium. Estados de erro, vazio, debounce e concorrência também são testados
por componente. As capturas foram revisadas em desktop e mobile.

`RISCO IDENTIFICADO`: evidências locais não comprovam desempenho ou dados de
produção. Preferência manual #214 e OC98 #211 não estão nesta base; o painel usa
somente os tokens existentes, compatíveis com a mudança de `data-theme`.
