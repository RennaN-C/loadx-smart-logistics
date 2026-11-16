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

## Issue #430 — matriz geométrica e multi-caminhão

`CONFIRMADO`: `benchmark_scalability.py` e `scalability_cases.py` complementam
o perfil leve da OC21. Usam somente dados sintéticos, UUIDs determinísticos e
dez perfis: homogêneo, heterogêneo, não empilhável, frágil, entregas, capacidades
diferentes, sobrecapacidade, denso, distribuição necessária e adversarial.
Dimensões/peso não causam rejeições triviais nos perfis homogêneo/denso.

Execute de `backend`, em ambiente **isolado**, sem outras medições concorrentes:

```bash
python -m benchmarks.benchmark_scalability --operations engine \
  --counts 25 50 100 200 --output /tmp/loadx-benchmarks/baseline-engine.json
python -m benchmarks.benchmark_scalability --operations multi \
  --profiles dense distribution fleet --truck-counts 1 2 3 5 10 \
  --output /tmp/loadx-benchmarks/baseline-multi.json
python -m benchmarks.benchmark_scalability --operations compare \
  --profiles dense heterogeneous --truck-counts 2 3 5 10 \
  --output /tmp/loadx-benchmarks/baseline-comparison.json
python -m benchmarks.benchmark_scalability --operations engine \
  --profiles dense heterogeneous adversarial deliveries --counts 100 \
  --instrument --output /tmp/loadx-benchmarks/profile.json
```

`--backend-root /caminho/checkout/backend` usa outro checkout da engine como
oráculo/base; o construtor dos cenários continua sendo este runner. Conserve a
revisão e o hash dos arquivos indicados no JSON. Execuções posteriores usam os
mesmos argumentos e entradas. Não misture números de profiling/tracemalloc com
tempos oficiais: instrumentação altera significativamente o custo.

`CONFIRMADO`: cada caso usa subprocesso novo, timeout de parede (`--timeout`,
default 45 s) e limite de espaço de endereçamento (`--memory-mib`, default
768 MiB); revisões atuais também limitam CPU no filho. Timeout mata/recolhe o
filho; Ctrl+C encerra o filho e propaga a interrupção. Não há benchmark pesado
na CI padrão. Os limites do runner são contenção de laboratório, **não SLO HTTP**.

Warmup (default 1) não entra nas três amostras oficiais. JSON registra amostras,
mínimo/mediana/máximo/desvio padrão; p95 fica nulo com essa amostragem pequena.
RSS é `ru_maxrss` Linux (KiB), incluindo intérprete/inputs/resultados e cópia
canônica, capturado antes do oráculo físico. O pai também observa VmHWM, quando
possível, inclusive em casos interrompidos. Tracemalloc é opcional, numa rodada
separada com `--allocations`; não mede toda a memória residente.

`--instrument` executa uma rodada separada com cProfile e contagem de chamadas,
estados criados e pares de profundidade visitados pela implementação-base.
`classify_aabb_relation` conta avaliações exatas de colisão (incluindo a final);
`_contact_rectangle` conta avaliações de contato de apoio; os demais nomes de
função não devem ser interpretados como pares ou estados. Linhas de profiler
distinguem expansão, ordenação, posicionamento, sequência e revalidação.

`CONFIRMADO`: os resultados passam por oráculo independente que usa células
inteiras em centímetros, checando colisão, apoio integral, flags, ancestrais,
profundidade, sequência, peso, rotação e conservação de identidades. O oráculo
fica fora das amostras de tempo, mas dentro do timeout do processo. Um caso que
não termina essa verificação não é registrado como sucesso. Canonicalização e
SHA-256 permitem comparar **todo** o resultado antes/depois, não apenas métricas.

Somente após avaliar a progressão anterior, execute experimentalmente:

```bash
python -m benchmarks.benchmark_scalability --operations engine \
  --profiles dense heterogeneous adversarial --counts 500 --experimental-limit \
  --timeout 30 --output /tmp/loadx-benchmarks/experimental-500.json
```

`RISCO IDENTIFICADO`: `--experimental-limit` altera somente constantes da engine
e comparação **dentro do filho de benchmark**. Não é configuração da aplicação,
não afeta HTTP/preflight, não persiste, nem autoriza 500/1.000 em produção.
Avaliar 1.000 exige evidência favorável em 500. Casos timeout/memória/erro ou
distribuição incompleta válida são explicitamente distintos de sucesso completo.
O runner exige Linux (`resource`, `/proc` e cgroup v2). Não executar no Render.

Por segurança, `--output` aceita somente um nome JSON simples ou um arquivo em
`/tmp/loadx-benchmarks/`. O diretório é criado como privado (0700), e a escrita
recusa symlinks, hardlinks e caminhos arbitrários. Arquivos de evidência no Git
são copiados **após** revisão manual; o benchmark não escreve diretamente no repositório.

Resultados e decisão de limite: [Issue #430](../../docs/evidencias/issue-430/README.md).

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
