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
