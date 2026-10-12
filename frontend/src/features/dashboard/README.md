# Feature: dashboard — Visão geral

`CONFIRMADO`: a rota `/` consolida o início OC25 e os indicadores operacionais
OC74 na manutenção #206. ADMIN e LOGISTICS_MANAGER veem os quatro grupos reais
(frota, viagens, entregas, ocorrências) de `GET /operational-indicators`.
Períodos `CURRENT_SNAPSHOT`/`ALL_TIME` permanecem explícitos. Indicadores
complementares ficam em detalhes expansíveis, sem métricas derivadas.

`CONFIRMADO`: o contador de caminhões do cadastro não é repetido para gestores;
a frota vem somente da OC69. Produtos, clientes, motoristas e pedidos continuam
usando os totais de seus envelopes de paginação. Pedidos recentes têm links
`/orders?order=ID`, reabrindo o detalhe persistido. Falha de um bloco não derruba
os demais; há retentativa para indicadores e resumo de cadastros/pedidos.

`CONFIRMADO`: CHECKER mantém o resumo de recursos autorizados, sem consultas de
clientes, motoristas ou indicadores globais. DRIVER mantém `DriverTrips`, com
recorte de viagens aplicado pelo backend e links de detalhe existentes. Nenhum
perfil é ampliado. `/operations` redireciona para a raiz somente para ADMIN e
LOGISTICS_MANAGER; os demais recebem acesso negado antes de qualquer consulta.

`CONFIRMADO`: apenas os indicadores com destino existente oferecem navegação
contextual — disponibilidade aponta para `/trucks?tab=availability`. Não há
listagem geral de viagens/entregas nesta consolidação; a central OC93 permanece
fora do escopo. Nenhum botão de métrica leva a uma rota fictícia.
