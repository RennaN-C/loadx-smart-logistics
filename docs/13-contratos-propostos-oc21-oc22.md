# Contratos propostos para a OC21 e a OC22

## Estado deste documento

`RECOMENDAÇÃO`: proposta de contrato público para as duas ocorrências que estão
com o núcleo pronto e a API bloqueada. Escrito pelo Desenvolvedor 3, do ponto de
vista de quem vai consumir.

`CONFIRMADO`: nada aqui está aprovado por constar neste documento. As duas
ocorrências pertencem ao Desenvolvedor 2, e cada campo abaixo precisa do aceite
dele antes de virar código.

`CONFIRMADO`: o `README` de `backend/app/modules/load_planning` marca as duas
como `DECISÃO NECESSÁRIA` e lista o que falta decidir. Este documento responde
item por item daquela lista, para a decisão ser sobre um texto concreto em vez
de uma folha em branco.

`CONFIRMADO`: as duas fatias internas já existem e estão testadas na branch
`Dev2_backend` — `optimizer/comparison.py` e `explanation.py`. As respostas
propostas abaixo são casca fina sobre o que aquelas funções já devolvem, de
propósito: quanto menos o contrato exigir de novo, mais barato ele sai.

---

## OC21 — comparação entre caminhões

### O que já existe

`compare_trucks(candidates, order_items)` devolve
`tuple[TruckComparisonResult, ...]`, e cada resultado é
`{ truck_id, load_plan: LoadPlanResult }`. O `LoadPlanResult` é o mesmo que o
cálculo normal produz: `capacity`, `placed_volumes`, `rejected_volumes` e
`metrics`. Nada é ranqueado e nada é persistido.

### Endpoint proposto

```
POST /api/v1/load-plans/compare-trucks
```

### Request

```json
{
  "truck_ids": ["uuid", "uuid"],
  "order_ids": ["uuid", "uuid"]
}
```

- `truck_ids`: mínimo 2, máximo 10, sem repetição.
- `order_ids`: mínimo 1, sem repetição. Mesma regra de elegibilidade do
  `POST /load-plans` — só pedido em `READY`.

O limite de 10 já é o do núcleo. O mínimo de 2 é o que separa comparar de
calcular: com um caminhão só, o caminho é o `POST /load-plans` normal.

### Response `200`

```json
{
  "algorithm_version": "heuristic-v1",
  "results": [
    {
      "truck": {
        "id": "uuid",
        "plate": "ABC1D23",
        "model": "Baú médio",
        "width_cm": 240,
        "height_cm": 260,
        "length_cm": 600,
        "max_weight_kg": 8000
      },
      "occupancy_percent": 78.42,
      "total_weight_kg": 6120.5,
      "used_volume_cm3": 29350000,
      "internal_volume_cm3": 37440000,
      "loaded_count": 113,
      "unloaded_count": 4,
      "rejections": [
        { "reason": "WEIGHT_EXCEEDED", "count": 3 },
        { "reason": "NO_VALID_POSITION", "count": 1 }
      ]
    }
  ]
}
```

Justificando cada escolha pelo que a tela precisa:

- **`results` na ORDEM em que os `truck_ids` chegaram.** Ordenar por qualquer
  métrica seria ranquear pela porta dos fundos, e a decisão do time é não
  ranquear. A tela mostra em cards lado a lado, sem posição.
- **`truck` embutido, não só o id.** Sem isso a tela faria N chamadas a
  `/trucks/{id}` só para escrever a placa no card. O caminhão é snapshot do
  momento da comparação, como já acontece no plano persistido.
- **`rejections` agregado por motivo, com contagem.** A tela não lista volume
  rejeitado nesta etapa: o que o gestor precisa saber é *por que* um caminhão
  deixou carga de fora, e "3 por peso" responde isso. A lista item a item já
  existe no plano persistido, depois que ele escolher.
- **`algorithm_version` na raiz**, não por resultado: todos os candidatos passam
  pela mesma engine, e repetir por item seria ruído.
- **Sem `score`, sem `rank`, sem `winner`, sem `recommended`.** Combinado com o
  time. A tela não inventa vencedor.

### Decimais e nomes

Conforme `D06`/`ADR-016`, `occupancy_percent` e `total_weight_kg` saem como
número JSON, não string. Campos em `snake_case`, como o resto da API.

### Códigos de erro propostos

| Situação | HTTP | `code` |
|---|---|---|
| Menos de 2 ou mais de 10 caminhões, ids repetidos, lista vazia | 422 | `VALIDATION_ERROR` |
| Algum `truck_id` não existe | 404 | `LOAD_PLAN_TRUCK_NOT_FOUND` |
| Algum caminhão está inativo | 409 | `LOAD_PLAN_TRUCK_INACTIVE` |
| Algum `order_id` não existe | 404 | `LOAD_PLAN_ORDER_NOT_FOUND` |
| Algum pedido não está em `READY` | 409 | `LOAD_PLAN_ORDER_NOT_ELIGIBLE` |
| Produto de um pedido não existe mais | 404 | `LOAD_PLAN_PRODUCT_NOT_FOUND` |

Reaproveitar os códigos que o `POST /load-plans` já usa é proposital: o
frontend já traduz todos eles em `loadPlansErrorMessages.ts`, e a tela de
comparação herda as mensagens sem uma linha nova.

### As perguntas em aberto, respondidas

- **Ranking e desempates**: não existem. A ordem é a da entrada.
- **Vencedor**: não existe.
- **Persistência**: nenhuma. A comparação não cria `load_plan`, não grava
  histórico e não reserva nada. O usuário escolhe um caminhão e segue pelo
  `POST /load-plans` normal, que é o único caminho que persiste.
- **Duplicatas**: `truck_ids` repetidos são erro de validação, não são
  deduplicados em silêncio. Deduplicar mudaria a resposta sem avisar, e a tela
  mostraria menos cards do que o usuário marcou.
- **Caminhão inativo**: erro `409`, a comparação inteira falha. Ignorar o
  inativo em silêncio cairia no mesmo problema das duplicatas.
- **Falhas parciais**: **não existem**. Ou todos os candidatos calculam, ou a
  requisição falha inteira. Um resultado parcial obrigaria a tela a explicar
  por que um card veio vazio, e o valor da comparação é justamente olhar os
  candidatos lado a lado.
- **RBAC**: `LOGISTICS_MANAGER` apenas. Comparar é passo de planejamento, e
  quem cria plano hoje é o gestor. `ADMIN` e `CHECKER` não precisam — se o time
  preferir incluir `ADMIN` por simetria com o resto, a tela acompanha sem
  mudança.

### Custo estimado

Dez caminhões é dez execuções completas da engine, síncronas, com o teto de 200
volumes expandidos cada. `DECISÃO NECESSÁRIA`: se o tempo de resposta passar do
aceitável em teste com carga real, o limite de 10 deve cair antes de a v1.0.0
sair.

---

## OC22 — explicar o planejamento

### O que já existe

`explanation.py` monta `LoadPlanExplanationContext` a partir do plano
persistido: snapshot do caminhão, volumes colocados e rejeitados, motivos,
posições, rotações, sequência e `algorithm_version`. É determinístico e não
chama provider nenhum.

### Endpoint proposto

```
POST /api/v1/load-plans/{load_plan_id}/explanation
```

`POST` e não `GET` porque a chamada tem custo real — provider externo — e não
deve ser cacheada nem repetida por navegação. Sem corpo.

### Response `200`

```json
{
  "source": "AI",
  "explanation": "Texto corrido em português...",
  "generated_at": "2026-08-27T21:40:00Z",
  "algorithm_version": "heuristic-v1"
}
```

- **`source`** é `"AI"` ou `"FALLBACK"`. A tela mostra a origem junto do texto,
  conforme decidido — quem lê precisa saber se aquilo veio de um modelo ou do
  texto determinístico.
- **`explanation`**: texto puro, sem HTML e sem Markdown. A tela renderiza como
  texto; aceitar marcação abriria injeção de conteúdo vindo de um modelo.
- **`generated_at`**: a explicação descreve um plano num instante. Se o plano
  for recalculado depois, a tela mostra a data para o usuário perceber.

`CONFIRMADO`: a resposta **não** carrega ação, link de aprovação nem sugestão de
mudança de estado. A tela não aprova nada a partir da explicação, conforme
decidido pelo time.

### Códigos de erro propostos

| Situação | HTTP | `code` |
|---|---|---|
| Plano não existe | 404 | `LOAD_PLAN_NOT_FOUND` |
| Provider fora do ar e fallback desligado | 503 | `EXPLANATION_UNAVAILABLE` |
| Provider recusou por limite de uso | 429 | `RATE_LIMITED` |

`RECOMENDAÇÃO`: com o fallback ligado, o provider fora do ar devolve `200` com
`source: "FALLBACK"` em vez de erro. É melhor entregar a explicação
determinística do que uma tela de erro — e a tela já mostra a origem.

### RBAC

`ADMIN` e `LOGISTICS_MANAGER`. `CHECKER` não precisa explicar plano; ele
confere carga.

### O que a tela vai fazer

Botão "Explicar planejamento" no cabeçalho do plano, com estado de espera
enquanto o provider responde, o texto num painel abaixo e a origem marcada. Erro
usa o mesmo mapeamento das outras telas. Sem botão de aprovar em lugar nenhum
desse fluxo.

### As perguntas em aberto, respondidas

- **Endpoint, request, response, schema público**: acima.
- **Fallback**: `200` com `source: "FALLBACK"`, não erro.
- **Dados enviados ao modelo**: só o que `LoadPlanExplanationContext` já monta —
  medidas, posições, métricas, motivos de rejeição. `CONFIRMADO`: não deve sair
  daqui nada de cliente, endereço, documento ou nome de pessoa. O contexto atual
  já não inclui esses campos, e isso precisa continuar valendo.
- **Prompt final**: pertence ao Desenvolvedor 4, que é quem integra o provider.
  A tela não depende dele.

---

## O que o frontend faz assim que isto for aprovado

`CONFIRMADO`: a interface das duas está desenhada e depende só do contrato.

- **OC21**: seleção de 2 a 10 caminhões na tela de planejamento, botão de
  comparar, e os resultados em cards lado a lado com ocupação, peso,
  carregados, não carregados e as rejeições agrupadas por motivo. Sem vencedor.
  O usuário escolhe um caminhão e segue pelo fluxo normal de criação.
- **OC22**: botão, espera, texto, origem e erros.

As mensagens de erro das duas já existem em
`frontend/src/features/load-planning/components/loadPlansErrorMessages.ts`,
porque a proposta reaproveita os códigos atuais.
