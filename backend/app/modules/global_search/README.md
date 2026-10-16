# OC107 — Busca global

`CONFIRMADO`: `GET /api/v1/search?search=...&limit_per_category=5` agrega as
primeiras páginas das consultas públicas da OC95, sem acessar tabelas de outros
módulos diretamente. `GlobalSearchService` compõe Order/Customer/Truck/DriverService
e TripService; repositories existentes executam filtros, COUNT e LIMIT no PostgreSQL.
Não há um segundo mecanismo de indexação ou filtragem de registros em memória.

`CONFIRMADO`: termo obrigatório com 2–120 caracteres após trim; limite 1–10 por
categoria, default 5. Substring literal case-insensitive, acentos preservados
(conforme OC95); `%`, `_` e `\` escapados. Viagens acrescentam somente o filtro
interno por UUID ao repository/service existente; `GET /trips` não muda de contrato.
Ordenação por categoria e `created_at DESC, id DESC` dentro de cada consulta.
Resposta `results` contém somente `category`, `id`, `title` e `href`, sem totais,
metadados de categorias restritas, documentos, endereços ou dados de conta.

| Perfil | Categorias/campos pesquisáveis |
|---|---|
| ADMIN / LOGISTICS_MANAGER | Pedidos (UUID próprio/cliente, nome do cliente), clientes (nome/cidade), caminhões (placa/modelo), motoristas (nome), viagens (UUID próprio) |
| CHECKER | Pedidos (UUID próprio/cliente, sem consulta de nomes), caminhões (placa/modelo) |
| DRIVER | Somente UUID das viagens próprias, com vínculo existente e motorista ativo |

`CONFIRMADO`: cadastros arquivados são omitidos, sem interferir na disponibilidade
operacional temporária. Pedidos/viagens históricos continuam pesquisáveis. O
nome do cliente nunca é título de pedido. Sem vínculo válido, DRIVER recebe 403;
autenticação ausente/inválida recebe 401; parâmetros inválidos, 422. Não há busca
por CPF/CNPJ, e-mail, telefone ou CNH. Endpoint herda Cache-Control no-store.

`CONFIRMADO`: pedidos/viagens usam os detalhes existentes. Cadastros abrem suas
listagens existentes com o mesmo termo em `search` e aba apropriada. Como a busca
usa até 10 registros recentes e a listagem inicia com 20 na mesma ordenação,
os resultados selecionados estão na primeira página sem precisar de tela nova.
O filtro é representado na URL para funcionar em F5 e navegação anterior/próxima.

`CONFIRMADO`: limite de sugestões, não paginação de uma coleção global; decisão
registrada na ADR-039. A implementação reaproveita também os COUNT existentes e
carrega somente as páginas limitadas. Teste garante quantidade constante de SQL
(até 12 consultas para gestor), inclusive com itens de pedido via selectinload;
nenhum N+1. Não há necessidade estrutural de migration ou extensão PostgreSQL.

`RISCO IDENTIFICADO`: buscas parciais ILIKE/UUID convertido podem usar varredura
sequencial, como na OC95. Avaliar EXPLAIN/latência com volume representativo antes
de criar índices ou prometer SLA; não foram inventadas métricas de produção.
