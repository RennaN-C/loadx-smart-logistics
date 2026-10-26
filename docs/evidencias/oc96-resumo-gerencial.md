# OC96 — resumo gerencial filtrado (primeira etapa)

Esta PR adiciona resumo gerencial calculado no PostgreSQL e exportacao CSV/PDF,
com os mesmos filtros de periodo, caminhao e motorista em todos os endpoints.

- GET /api/v1/reports/management-summary
- GET /api/v1/reports/management-summary.csv
- GET /api/v1/reports/management-summary.pdf

Parametros obrigatorios: start e end em ISO 8601 com fuso. O fim e exclusivo.
Intervalos invalidos ou maiores que 93 dias sao rejeitados.

Sem calculos no frontend, sem dados pessoais e com permissao reports.read.
Em distribuicao multi-caminhao, cada perna concluida e contada uma vez;
orders_with_completed_leg representa pedidos com pelo menos UMA perna concluida
no periodo e nao pode ser interpretado como pedidos totalmente entregues.

Ainda faltam UI, indicadores de excecoes OC94, testes API com PostgreSQL e
validacao de volumes grandes antes do fechamento da OC96.
