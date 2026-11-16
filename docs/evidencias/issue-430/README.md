# Issue #430 — escalabilidade da heuristic-v1

> `CONFIRMADO`: este documento registra a entrega e as medições históricas de
> `c366fb9e`. A integração posterior com `desenvolvimento` está documentada em
> [integração e revalidação](integracao-desenvolvimento.md). Os tempos e resultados
> RAW abaixo permanecem os originalmente medidos; não são novas medições da base
> integrada. O merge posterior ocorreu somente nesta branch de trabalho.

`CONFIRMADO`: investigação e otimização na branch
`joao/expandir-capacidade-otimizador`, Identificador N/A. Base obtida por fetch:
`cb9c6f7d7f0e1b2829cae938a15e2fc63d6be09e`. A Issue permanece aberta;
esta entrega não cria PR, merge ou deploy. Dados exclusivamente sintéticos.

## Método e escopo

`CONFIRMADO`: medições de 15/11/2026 no ambiente Cloud isolado do Render:
Python 3.12.14, Linux x86_64, Intel Xeon Platinum 8573C, três CPUs visíveis,
quota cgroup de duas CPUs e limite de memória do container de 8 GiB. Cada
subprocesso tem limite de espaço de endereçamento de 768 MiB. As capacidades
e os tempos desse ambiente **não** descrevem o Render publicado.

Um processo por caso; sem benchmarks concorrentes. Dez perfis A–J para a engine,
25/50/100/200 volumes. Distribuição cobre dense/distribution/fleet com
1/2/3/5/10 candidatos; comparação independente cobre dense/heterogeneous com
2/3/5/10. Um warmup fora das três amostras oficiais; perf_counter, mínimo,
mediana, máximo e desvio padrão. P95 não é inferido de três amostras.

O orçamento de laboratório é do **processo inteiro**: importação, warmup,
amostras, canonicalização e verificação independente. Timeout numa rodada de
três amostras não prova que uma única chamada excede o mesmo valor. Os pilotos
maiores e rodadas suplementares distinguem explicitamente essa situação.
Revisões recentes do runner também têm teto de CPU no filho e observam VmHWM.
Um piloto inicial de desenvolvimento com medições sobrepostas foi descartado;
não compõe os JSONs oficiais. Instalação/coleção de dependências foi preparação,
sem alteração de entradas, e não é evidência de capacidade de produção.

`CONFIRMADO`: RSS (`peak_rss_kib`) é o pico do processo Linux antes do oráculo
por células; inclui intérprete, inputs, resultados, warmup e cópia canônica.
`observed_process_peak_rss_kib` também pode incluir o oráculo independente e
não deve ser atribuído somente à engine. Nos primeiros casos censurados não
houve observação de RSS pelo pai; não há número inventado para esses casos.
Tracemalloc não foi usado como substituto de RSS.

Profile separado com cProfile, sem misturar seus tempos às amostras oficiais.
Os JSONs guardam chamadas por função e linhas do profiler. Contagem de estados
é construção de _SearchState (inclui inicial); attempt_count conta execuções
efetivas da engine, não cache hits nem total de veículos. Candidatos avaliados
são callbacks que já passaram por limites; classify_aabb_relation conta pares
exatos, _contact_rectangle conta testes de apoio e depth_pair_visits conta pares
visitados pelo algoritmo-base. Funções geradoras não são contagens de volumes.

`CONFIRMADO`: SHA-256 do diretório optimizer da referência:
`937477ed8ba09bb0f43cab3dbcabd92798eed5f4dd43fb5b490e7f612d2c413d`.
Da implementação medida:
`e9e2bb178419128c3066d107ec14d49d2eefb39fc8bfd802e3b4e2b377c6b4cf`.
O HEAD Git em alguns JSONs ainda é a base porque as alterações estavam sem
commit; o hash dos arquivos identifica o código efetivamente medido.

`RISCO IDENTIFICADO`: medições são locais/descritivas, com amostragem pequena e
host compartilhado. Não são SLO, p95 de produção nem teste de concorrência HTTP.
Tempo cronometrado é cálculo puro. Canonicalização/JSON do oráculo ficam fora
das amostras; não são uma medição da serialização Pydantic. Persistência/HTTP de
500 não foram habilitados nem usados como argumento para ampliar o contrato.

## Mudanças e prova de equivalência

`CONFIRMADO`: índice espacial append-only, por chamada, com até 8³ células.
Para inteiros, os índices ocupados por [x,x+w) vão de x//s a (x+w-1)//s. Se dois
volumes têm sobreposição positiva, compartilham pelo menos uma célula nos três
eixos. Portanto, a filtragem não pode remover um par em colisão. Candidatos
potenciais continuam passando pelo predicado AABB original; o índice permite
falsos candidatos geométricos, nunca uma aprovação aproximada. Referências no
índice são limitadas a 512*N e liberadas ao terminar a chamada. A varredura
completa da revalidação final ignora esse índice.

Profundidade: todos os pares entre grupos são válidos se, e somente se, o menor
valor de distância do grupo posterior é >= ao maior valor dos anteriores.
Agrupamento e extremos inteiros substituem O(N²) pares por O(N + G log G), sem
alterar porta, igualdade ou validação de input. G é o número de sequências.

Pontos, prioridade de rotação, first-fit, ordenação, motivos, Decimal, união
exata de apoios, ancestrais/fragilidade, Kahn e revalidação permanecem. A busca
multi e seu cache por capacidade/identidades não foram alterados. Não se criou
cache global, nova dependência, migration ou versão observável de heurística.

Os snapshots versionados foram obtidos na referência, não na engine otimizada.
Comparação usa o resultado completo, incluindo identidades, atributos,
coordenadas, rotações, rejeições, sequência, métricas, caminhões, atribuições e
attempt_count. O teste de determinismo inverte volumes e caminhões e repete
execuções; testes concorrentes verificam isolamento por chamada. Oráculos de
intervalos inteiros e profundidade par a par conferem os caminhos otimizados.
O verificador manual por células em centímetros valida física sem importar os
validadores de colisão/apoio/profundidade da engine. Uma falha injetada no índice
precisa ser detectada pela revalidação final, e é coberta por teste.

## Reprodução

Ver [runner e comandos](../../../backend/benchmarks/README.md). Para referência:

```bash
git worktree add --detach /tmp/loadx-issue430-reference cb9c6f7d7f0e1b2829cae938a15e2fc63d6be09e
cd backend
python -m benchmarks.benchmark_scalability \
  --backend-root /tmp/loadx-issue430-reference/backend --operations engine \
  --timeout 30 --output ../docs/evidencias/issue-430/baseline-engine.json
# Repetir sem --backend-root para medir o código otimizado.
python -m benchmarks.summarize_scalability ../docs/evidencias/issue-430
```

`CONFIRMADO`: os JSONs registram argumentos, revisão, ambiente, amostras e
resultados. [measurements.csv](measurements.csv) consolida todos os casos;
[comparison-summary.json](comparison-summary.json) compara hashes antes/depois
e não atribui valores a casos censurados. Dados RAW são retidos por solicitação
específica desta Issue; a exceção em .gitignore limita-se a esta pasta.

## Limites e decisões

`CONFIRMADO`: antigo=200, proposto nesta entrega=200, efetivamente liberado=200
volumes físicos. Comparação continua 2–10 candidatos; distribuição mantém dez
partes e fronteira de 64 estados. API e UI permanecem coerentes, inclusive erro
422/LOAD_PLAN_VOLUME_LIMIT_EXCEEDED antes da expansão, testado também com 500 e
1.000. Nenhuma constante pública foi elevada pelo benchmark.

`RISCO IDENTIFICADO`: a matriz cobre até dez candidatos; o preflight automático
pode fornecer mais que dez elegíveis. Os 64 estados não limitam o total de
execuções da engine. Apoio completo por aceitação e muitos candidatos inválidos
continuam podendo dominar grandes cargas. O inventário detalha os limites e a
renderização atual de todos os volumes, sem virtualização para milhares.

`PENDENTE DE DEFINIÇÃO`: orçamento HTTP/CPU/RAM/concorrência efetivo do Render e
custos end-to-end com um contrato maior. Não inventar timeout de plataforma.
`DECISÃO NECESSÁRIA`: Rennan deve avaliar [a proposta assíncrona](proposta-assincrona.md)
antes de introduzir uma fila computacional ou aprovar capacidade maior.
Não reutilizar automaticamente a outbox de notificações OC109 para esse fim.

Inventário: [inventario.md](inventario.md). As seções abaixo registram os resultados medidos e as validações.

## Engine: matriz de 25 a 200 volumes

`CONFIRMADO`: medianas em segundos; RSS antes do oráculo em MiB. Cada linha tem
três amostras completas, salvo timeout explicitamente censurado. A rodada
otimizada completou 39 dos 40 casos; múltiplas entregas/200 atingiu o orçamento
agregado de 30 s. Perfis com restrições podem rejeitar volumes legitimamente.
Min/max/desvio e amostras estão nos JSONs/CSV.

| Perfil | N | Base s | Otimizada s | RSS base/nova MiB | Colocados | Rejeitados |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| homogeneous | 25 | 0.0176 | 0.0073 | 15.1 / 14.6 | 25 | 0 |
| homogeneous | 50 | 0.0862 | 0.0251 | 14.8 / 14.9 | 50 | 0 |
| homogeneous | 100 | 0.5081 | 0.0974 | 15.0 / 15.2 | 100 | 0 |
| homogeneous | 200 | 2.2758 | 0.9431 | 15.4 / 16.2 | 200 | 0 |
| heterogeneous | 25 | 0.0309 | 0.0180 | 14.8 / 14.8 | 25 | 0 |
| heterogeneous | 50 | 0.2037 | 0.0772 | 14.9 / 14.9 | 50 | 0 |
| heterogeneous | 100 | 1.6161 | 0.4241 | 15.2 / 15.5 | 100 | 0 |
| heterogeneous | 200 | timeout | 2.2790 | n/d / 16.2 | 200 | 0 |
| non_stackable | 25 | 0.0202 | 0.0077 | 14.8 / 14.6 | 25 | 0 |
| non_stackable | 50 | 0.0445 | 0.0258 | 14.8 / 14.9 | 50 | 0 |
| non_stackable | 100 | 0.2432 | 0.1033 | 15.0 / 15.2 | 100 | 0 |
| non_stackable | 200 | 1.7780 | 0.3778 | 15.2 / 16.2 | 200 | 0 |
| fragile | 25 | 0.0091 | 0.0073 | 14.5 / 14.6 | 25 | 0 |
| fragile | 50 | 0.0679 | 0.0250 | 14.6 / 14.9 | 50 | 0 |
| fragile | 100 | 0.4016 | 0.0973 | 14.8 / 15.2 | 100 | 0 |
| fragile | 200 | 2.1453 | 0.9350 | 15.1 / 16.2 | 200 | 0 |
| deliveries | 25 | 0.0098 | 0.0072 | 14.8 / 14.6 | 25 | 0 |
| deliveries | 50 | 0.0457 | 0.0261 | 14.8 / 14.9 | 50 | 0 |
| deliveries | 100 | 0.2645 | 0.0950 | 15.0 / 15.2 | 100 | 0 |
| deliveries | 200 | timeout | timeout | n/d / n/d | n/d | n/d |
| fleet | 25 | 0.0243 | 0.0171 | 15.0 / 14.8 | 18 | 7 |
| fleet | 50 | 0.0551 | 0.0422 | 14.9 / 14.9 | 15 | 35 |
| fleet | 100 | 0.1087 | 0.0786 | 15.1 / 15.2 | 14 | 86 |
| fleet | 200 | 0.4152 | 0.2392 | 15.8 / 15.8 | 20 | 180 |
| over_capacity | 25 | 0.0059 | 0.0059 | 14.8 / 14.6 | 12 | 13 |
| over_capacity | 50 | 0.0261 | 0.0165 | 15.0 / 14.9 | 24 | 26 |
| over_capacity | 100 | 0.1354 | 0.0610 | 15.4 / 15.2 | 48 | 52 |
| over_capacity | 200 | 0.8657 | 0.2862 | 15.9 / 15.9 | 96 | 104 |
| dense | 25 | 0.0130 | 0.0124 | 14.6 / 14.8 | 25 | 0 |
| dense | 50 | 0.0596 | 0.0442 | 14.9 / 15.0 | 50 | 0 |
| dense | 100 | 0.3429 | 0.1865 | 15.2 / 15.4 | 100 | 0 |
| dense | 200 | 2.2524 | 1.1194 | 16.1 / 16.2 | 200 | 0 |
| distribution | 25 | 0.0094 | 0.0083 | 14.8 / 14.6 | 25 | 0 |
| distribution | 50 | 0.0446 | 0.0295 | 15.0 / 14.9 | 50 | 0 |
| distribution | 100 | 0.2539 | 0.1141 | 15.4 / 15.2 | 100 | 0 |
| distribution | 200 | 1.7275 | 0.7379 | 16.3 / 16.1 | 200 | 0 |
| adversarial | 25 | 0.0406 | 0.0270 | 15.0 / 14.9 | 25 | 0 |
| adversarial | 50 | 0.2030 | 0.1018 | 15.2 / 15.0 | 42 | 8 |
| adversarial | 100 | 1.1470 | 0.3678 | 15.5 / 15.4 | 67 | 33 |
| adversarial | 200 | timeout | 1.5434 | n/d / 16.0 | 126 | 74 |

## Profiling e contagem de trabalho

`CONFIRMADO`: rodada separada de 100 volumes; tempos de cProfile não são
latência oficial. O callback de candidatos tem exatamente a mesma contagem,
evidenciando preservação da ordem de tentativa. Pares AABB incluem a validação
final completa, que continua fora do índice.

| Perfil | Callbacks base/nova | Pares AABB base/nova | Contatos de apoio base/nova | Pares profundidade base/nova |
| --- | ---: | ---: | ---: | ---: |
| dense | 5050 / 5050 | 176550 / 19764 | 77560 / 77560 | 181500 / 0 |
| heterogeneous | 45453 / 45453 | 1374575 / 151855 | 20777 / 20777 | 181500 / 0 |
| adversarial | 38781 / 38781 | 901688 / 110039 | 49087 / 49087 | 56749 / 0 |
| deliveries | 5050 / 5050 | 176550 / 26412 | 0 / 0 | 181500 / 0 |

`CONFIRMADO`: no heterogêneo, is_collision_free caiu de 5,080 s para cerca
de 0,77 s perfilados (custos cumulativos, não somáveis). No denso otimizado,
_support_rejection_reasons ainda consumiu 0,566 s dos 0,903 s perfilados da engine.
Apoio não foi simplificado: permanecem 102 análises completas e 77.560 testes
de contato no caso denso. Pontos/rotações/revalidação têm custos registrados
separadamente. Recriar pontos consumiu cerca de 0,05 s nos cenários de 100;
não foi priorizado diante dos gargalos medidos. O cache da distribuição já
compartilhava cargas/capacidades idênticas; não foi substituído.

## Resultado de referência censurado

`CONFIRMADO`: a rodada suplementar, **uma amostra sem warmup**, completou o
heterogêneo de 200 em 16,900 s e o adversarial em 8,722 s; seus hashes também
integram o oráculo versionado. A rodada oficial de três amostras continua
registrada como censurada, sem substituir silenciosamente seus valores.
O caso de múltiplas entregas com 200 também atingiu 35 s numa tentativa única
na referência; não há hash antigo para esse caso. A equivalência da regra de
profundidade é coberta pelo oráculo par a par (729 configurações) e pela prova
por extremos, sem declarar equivalência experimental de uma execução que não
terminou. Há 39 snapshots completos da engine e seis da distribuição.

`CONFIRMADO`: o perfil da distribuição real de 200 volumes/dez caminhões criou
2.098 estados e fez dez chamadas físicas, tanto antes quanto depois. A fronteira
continua 64 e as atribuições são idênticas. Isso distingue estados gerados,
fronteira retida, candidatos e avaliações efetivas; não são a mesma métrica.

## Distribuição e comparação independente (até 200)

`CONFIRMADO`: todos os tempos/RSS por cenário e as 1/2/3/5/10 alternativas
estão no CSV/JSON. O perfil distribution força repartir a necessidade entre
veículos, em vez de rejeitar tudo por peso. Em 200 volumes, duas/três/cinco/dez
partes completas foram preservadas, com exatamente as identidades originais.
Dense pode escolher um único caminhão mesmo com dez candidatos: a capacidade
completa e a carga são idênticas, por isso o cache existente faz uma única
execução física. Fleet usa capacidades diferentes, sem compartilhar indevidamente
os resultados. Casos incompletos válidos não são propostas persistíveis.

A matriz de comparação independente mede o custo somado de cada candidato, sem
selecionar vencedor, sem persistência e sem aplicar o cache da distribuição.
As respostas preservam a ordem dos candidatos. Censura por orçamento agregado
não significa uma rejeição física ou desaparecimento de volumes.

## Experimentos controlados com 500 volumes

`CONFIRMADO`: uma execução sem warmup por cenário no piloto, com orçamento de
20 s por processo. Success da engine significa cálculo válido terminado, podendo
conter rejeições; não significa que toda a carga coube. Nos timeouts, contagens
e pico da engine são desconhecidos; o RSS observado inclui o processo/oráculo.

| Operação / perfil | Candidatos | Resultado | Tempo s | RSS engine / observado MiB | Colocados / restantes |
| --- | ---: | --- | ---: | ---: | --- |
| compare / dense | 2 | timeout | timeout 20 | n/d / 16.2 | n/d |
| compare / dense | 3 | timeout | timeout 20 | n/d / 16.2 | n/d |
| compare / heterogeneous | 2 | timeout | timeout 20 | n/d / 16.3 | n/d |
| compare / heterogeneous | 3 | timeout | timeout 20 | n/d / 16.3 | n/d |
| engine / homogeneous | 1 | success | 10.778 | 18.2 / 68.5 | 500 / 0 |
| engine / dense | 1 | success | 10.756 | 18.2 / 70.3 | 500 / 0 |
| engine / heterogeneous | 1 | success | 15.848 | 18.0 / 75.2 | 371 / 129 |
| engine / adversarial | 1 | success | 11.940 | 17.9 / 68.4 | 304 / 196 |
| engine / non_stackable | 1 | success | 3.104 | 18.2 / 78.8 | 500 / 0 |
| engine / deliveries | 1 | timeout | timeout 20 | n/d / 15.6 | n/d |
| multi / distribution | 5 | success | 2.359 | 22.9 / 32.8 | 500 / 0 |
| multi / distribution | 10 | success | 2.762 | 28.1 / 29.4 | 500 / 0 |
| multi / fleet | 5 | timeout | timeout 20 | n/d / 16.5 | n/d |
| multi / fleet | 10 | timeout | timeout 20 | n/d / 16.4 | n/d |
| multi / dense | 2 | success | 11.238 | 19.5 / 70.2 | 500 / 0 |
| multi / dense | 3 | success | 10.872 | 19.5 / 70.2 | 500 / 0 |
| multi / distribution | 2 | success | 3.768 | 20.4 / 55.7 | 500 / 0 |
| multi / distribution | 3 | success | 2.989 | 21.1 / 47.4 | 500 / 0 |
| multi / fleet | 2 | incomplete_valid | 9.967 | 20.5 / 38.9 | 144 / 356 |
| multi / fleet | 3 | timeout | timeout 20 | n/d / 16.5 | n/d |

`CONFIRMADO`: repetição adicional do denso/500, warmup=1 e três amostras,
com orçamento agregado de 60 s (não um novo timeout HTTP):
[10.77471642899991, 10.635092673000145, 11.736228815000231]; mediana **10.775 s**,
mínimo 10.635, máximo 11.736, desvio 0.600.
500 colocados, zero rejeitados; RSS da engine 18.52 MiB.
Todos os resultados repetidos têm o mesmo hash e passam pelo oráculo físico.

`CONFIRMADO`: houve distribuição real de 500 identidades entre 2, 3, 5 e 10
caminhões. Partições completas são disjuntas e conservam todas as identidades.
Entregas múltiplas/500 e comparação/500 tiveram timeout em tentativas únicas;
frota heterogênea maior também não terminou. Não houve OOM observado nem erro
de invariante nos casos concluídos. Timeout não foi promovido a sucesso.

`CONFIRMADO`: **1.000 não foi executado**: a etapa de 500 já mostrou timeouts
e crescimento significativo. Não existe evidência suficiente para avançar a
progressão com segurança operacional, muito menos habilitar esse limite HTTP.
Os testes com quantity=1.000 validam recusa antecipada, não suporte a essa carga.

`RECOMENDAÇÃO`: 500/1.000 devem aguardar orçamento de produto e desenho de job
persistido/isolation/cancelamento para cargas prolongadas, conforme a proposta.
Não basta o cenário denso completar em ~11 s no laboratório. A função pura não
mede concorrência HTTP, persistência das 500 linhas/snapshots, JSON público e
renderização de 500 meshes. O limite público permanece 200.

## Arquivos desta entrega

`CONFIRMADO`: inventário do diff auditado; somente Issue #430. Relatórios de
cobertura temporários, logs, ambientes virtuais, .env e builds ficam fora.

- `backend/app/modules/load_planning/README.md`
- `backend/app/modules/load_planning/optimizer/README.md`
- `backend/app/modules/load_planning/optimizer/engine.py`
- `backend/app/modules/load_planning/optimizer/geometry.py`
- `backend/app/modules/load_planning/optimizer/loading_sequence.py`
- `backend/benchmarks/README.md`
- `backend/benchmarks/benchmark_scalability.py`
- `backend/benchmarks/scalability_cases.py`
- `backend/benchmarks/summarize_scalability.py`
- `backend/tests/integration/test_load_planning_api.py`
- `backend/tests/unit/load_planning/scalability_reference.json`
- `backend/tests/unit/load_planning/test_scalability.py`
- `backend/tests/unit/load_planning/test_scalability_benchmark.py`
- `docs/evidencias/.gitignore`
- `docs/evidencias/issue-430/README.md`
- `docs/evidencias/issue-430/baseline-comparison.json`
- `docs/evidencias/issue-430/baseline-edge-200.json`
- `docs/evidencias/issue-430/baseline-engine.json`
- `docs/evidencias/issue-430/baseline-multi-profile.json`
- `docs/evidencias/issue-430/baseline-multi.json`
- `docs/evidencias/issue-430/baseline-profile.json`
- `docs/evidencias/issue-430/comparison-summary.json`
- `docs/evidencias/issue-430/experimental-500-comparison.json`
- `docs/evidencias/issue-430/experimental-500-engine.json`
- `docs/evidencias/issue-430/experimental-500-more-trucks.json`
- `docs/evidencias/issue-430/experimental-500-multi.json`
- `docs/evidencias/issue-430/experimental-500-repeated.json`
- `docs/evidencias/issue-430/inventario.md`
- `docs/evidencias/issue-430/measurements.csv`
- `docs/evidencias/issue-430/optimized-comparison.json`
- `docs/evidencias/issue-430/optimized-engine.json`
- `docs/evidencias/issue-430/optimized-multi-profile.json`
- `docs/evidencias/issue-430/optimized-multi.json`
- `docs/evidencias/issue-430/optimized-profile.json`
- `docs/evidencias/issue-430/proposta-assincrona.md`

## Validações finais

`CONFIRMADO`: executadas no Python 3.12 e PostgreSQL 16 exclusivo de testes:

- `python -m pytest -q tests/unit/load_planning tests/unit/test_multi_truck_optimizer.py`:
  **497 passed**, 15,86 s.
- `TEST_DATABASE_URL=<PostgreSQL local loadx_test> python -m pytest -q tests --cov=app --cov-report=term`:
  **3.304 passed**, sete warnings, 787,60 s; cobertura **95%**
  (16.933 statements, 881 missed). Inclui integração, E2E legado/multi,
  disponibilidade, persistência, idempotência, permissões, OpenAPI e migrations
  existentes. Nenhuma falha funcional; não foi necessário reproduzir falha de
  código na base. A coleta inicial sem duas dependências foi resolvida instalando
  o lockfile, sem mudança de dependências do repositório.
- Os novos testes HTTP cobrem 201, 500 e 1.000 volumes nas quatro operações
  (plano/comparação/preflight/optimize), mantendo 422 e impedindo expansão/escrita.
- `python -m ruff check .`: aprovado.
- `python -m ruff format --check .`: aprovado, 614 arquivos.
- `git diff --check` e `git diff --cached --check`: aprovados.
- Consolidador: **117 resultados completos comparados, zero divergências**.

`CONFIRMADO`: nenhum arquivo frontend foi alterado. Vitest/ESLint/TypeScript/
build/bundle/auditoria npm não foram executados nesta alteração backend; o
contrato e o limite consumidos pela UI permanecem os mesmos. Não há type check
backend adicional configurado na CI. Nenhuma migration criada; a cadeia existente
foi exercitada pela suíte real.

`PENDENTE DE DEFINIÇÃO`: CI remota e revisão externa após a auditoria solicitada.
O workflow atual dispara em PR ou push nas branches de integração/release, não
no push isolado desta branch. Não se abriu PR nem se alterou trigger para obter
um check artificial. Os comandos locais de backend são os mesmos da CI.

`RECOMENDAÇÃO`: revisar o diff e a proposta de job com Rennan antes de qualquer
ampliação. Os resultados comprovam otimização interna, não liberação síncrona
segura de 500/1.000. A Issue #430 permanece aberta para a decisão de capacidade.
