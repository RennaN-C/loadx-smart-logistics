# Benchmarks do backend

## OC21 - comparação entre caminhões

`CONFIRMADO`: `benchmark_truck_comparison.py` mede diretamente a função pura
`compare_trucks`, sem HTTP, banco ou persistência. A matriz fixa cobre 2, 5 e 10
caminhões com 10, 50, 100 e 200 volumes sintéticos. Cada caminhão de um caso
recebe exatamente a mesma carga.

O perfil sintético usa caixas empilháveis de `20 x 20 x 20 cm` e `2 kg`, com
caminhões limitados a `10 kg`. Assim, cada execução percorre a engine completa,
posiciona cinco volumes e rejeita deterministicamente os demais por peso. Isso
exercita tanto carregamentos quanto rejeições normais sem transformar o runner
básico em um teste de estresse da busca geométrica.

Execute a partir de `backend`:

```bash
python -m benchmarks.benchmark_truck_comparison --warmup 1 --iterations 3
```

Para consumir os resultados por outra ferramenta:

```bash
python -m benchmarks.benchmark_truck_comparison --warmup 1 --iterations 3 --json
```

O warmup não entra nas medições. Cada iteração medida usa
`time.perf_counter`, e o runner informa mínimo, mediana, média e máximo. Antes de
aceitar uma execução, ele valida a quantidade e a ordem dos resultados, a
conservação de todos os volumes e `algorithm_version = heuristic-v1`.

`RISCO IDENTIFICADO`: os números dependem de CPU, sistema operacional, carga da
máquina e versão do Python. Este benchmark básico não define SLA nem limiar de
aprovação; compare resultados somente em ambientes equivalentes.

## OC95 — busca e filtros server-side

`CONFIRMADO`: `benchmark_server_side_filters.py` captura as consultas reais dos
repositories (incluindo COUNT, SELECT paginado e selectinload dos itens) e roda
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` três vezes por statement. Dados
inteiramente fictícios; seeds em transação revertida, sem reset de schema ou
commit. Recusa banco diferente de `loadx_test`, versão diferente de PostgreSQL 16
ou banco ocupado. Rode depois da suíte, com migrations aplicadas, sem pytest
concorrente. Não é assertion temporal de CI.

```bash
# Na pasta backend; credenciais exclusivamente locais do compose.test.yaml.
APP_ENV=local DATABASE_URL=postgresql+psycopg://localhost/loadx \
TEST_DATABASE_URL=postgresql+psycopg://loadx_test:loadx_test_local@127.0.0.1:55432/loadx_test \
python -m benchmarks.benchmark_server_side_filters --rows 10000
```

`CONFIRMADO`: inventário nos models e migrations 0001/0002/0017:
B-tree `orders.customer_id`, `orders.status`, `orders.expected_delivery_at`,
`orders.customer_address_id`, `customers.name`, `products.name`, PKs UUID e
unicidades globais de `plate`, `code`, `document`, `license_number`.
`order_items.order_id` atende selectinload. Índices de documento/telefone/CNH
não autorizam busca por esses campos. B-tree de nome não atende, por si só,
ILIKE substring com curinga inicial; nenhum índice criado por checklist.

Medição em 13/10/2026, PostgreSQL 16 do Compose no Cloud Environment, Python
3.12.14: 10.000 linhas por cada um dos cinco recursos, 20.000 order_items;
100 nomes com Alvo, cadastros parcialmente arquivados, status/flags mistos,
page_size=20, sort_order=desc. Mediana de três execuções, cache aquecido:

| Consulta | Total filtrado | COUNT / SELECT (ms aproximados) | Plano principal |
| --- | ---: | ---: | --- |
| Pedidos por nome | 100 | 10,0 / 10,6 | Seq Scan orders + subconsulta customers, Sort top-N |
| Pedidos por nome + READY | 34 | 5,2 / 6,6 | Bitmap Heap/Index Scan status + subconsulta customers, Sort top-N |
| Pedidos só READY | 3.334 | 0,3 / 0,7 | Bitmap Heap/Index Scan status, Sort top-N |
| Pedidos por UUID | 1 | 16,7 / 16,3 | Seq Scan orders + subconsulta customers, Sort |
| Caminhões por busca + ativo | 85 | 3,5 / 4,3 | Seq Scan, Sort top-N |
| Produtos busca + restricted + ativo | 29 | 2,0 / 2,0 | Seq Scan, Sort top-N |
| Produtos busca + free + ativo | 56 | 2,4 / 2,3 | Seq Scan, Sort top-N |
| Clientes por busca + ativo | 85 | 4,6 / 4,7 | Seq Scan, Sort top-N |
| Motoristas por busca + ativo | 85 | 2,2 / 3,3 | Seq Scan, Sort top-N |

`CONFIRMADO`: as consultas adicionais de order_items usaram Index Scan,
0,016–0,072 ms, sem N+1. O JSON do runner mostra SQL sem valores pessoais,
árvore completa, planning time, buffers e execution time para reprodução.
Subconsulta de clientes projeta somente UUID; COUNT nunca multiplica pedidos.

`RECOMENDAÇÃO`: manter índices atuais; essa medição não mostrou necessidade de
migration, extensão pg_trgm ou GIN. Os scans são esperados para substring
arbitrária e UUID convertido em texto. `RISCO IDENTIFICADO`: dados reais mais
volumosos, cache frio, concorrência e paginação profunda precisam de novas
medições; esses números não representam SLA ou garantia de escala. Nenhum
limiar de milissegundos foi adicionado aos testes.

## Inventário de filtros OC95

`CONFIRMADO`: OrderListPage (cliente/referência e status), TruckListPage
(placa/modelo), ProductListPage (código/nome e restriction), CustomerPanel
(nome/cidade) e DriverPanel (nome) passaram ao servidor. Archive_status da OC105
já era server-side e continua combinável.

`RISCO IDENTIFICADO`: FleetStatusPage mantém available/unavailable e contadores
por página, porque FleetAvailabilityService expõe leitura individual depois de
paginar, sem predicado SQL público para reutilizar a autoridade. A agregação
get_summary existente carrega a frota e não atende às restrições desta OC.

`CONFIRMADO`: outros filters encontrados foram classificados como apresentação
ou seleção auxiliar: PlanBuilder (READY, fontes ativas e impedimentos recebidos),
CreateTripAction (motoristas ativos e status), OrderForm (fontes ativas),
PlanItemsTable (colocados/rejeitados), LoadingPage/checklist (pendentes),
reportMetrics (indicadores explicitamente por página), customerAddressesApi
(endereços ativos do cliente selecionado), visualização 3D, navegação/RBAC,
campos de formulário e edição de políticas. Não são buscas de coleção aprovadas
nas cinco telas da whitelist; não receberam novos filtros públicos na OC95.
