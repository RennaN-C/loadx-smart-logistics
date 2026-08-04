# Otimizador

Implementa a heurística tridimensional do LoadX.

## Entrada mínima

- dimensões e peso máximo do caminhão;
- lista de volumes individuais;
- dimensões, peso, rotação, fragilidade, empilhamento e sequência de entrega.

## Saída mínima

- volumes posicionados com X, Y, Z e dimensões utilizadas;
- ordem de carregamento;
- volumes rejeitados e motivo;
- ocupação percentual;
- peso total;
- versão do algoritmo.

## Etapas previstas

1. expandir quantidades em volumes individuais;
2. ordenar volumes;
3. gerar rotações permitidas;
4. gerar pontos candidatos;
5. validar limites;
6. validar colisões;
7. validar apoio e empilhamento;
8. escolher posição;
9. calcular métricas.

## Restrições

O otimizador não acessa banco, HTTP, FastAPI ou provedor de IA. Ele recebe objetos simples e retorna resultado determinístico.

## OC11 - capacidade do caminhão

`CONFIRMADO`: o cálculo inicial de capacidade fica em `capacity.py`.

Entrada:

- `internal_width_cm`;
- `internal_height_cm`;
- `internal_length_cm`;
- `max_weight_kg`.

Saída:

- dimensões internas preservadas em centímetros;
- `internal_volume_cm3`;
- `max_weight_kg`.

Regras:

- Dimensões internas devem ser maiores que zero.
- Peso máximo deve ser maior que zero.
- Peso máximo deve ser um `Decimal` finito.
- O cálculo é determinístico e não acessa banco, HTTP ou IA.

## OC12 - volume individual e expansão

`CONFIRMADO`: `contracts.py` contém contratos imutáveis para o item antes da expansão, a identidade individual e o volume expandido. `volumes.py`:

- calcula `width_cm * height_cm * length_cm` com inteiros positivos;
- exige peso positivo e finito em `Decimal`;
- exige uma sequência ordenada de itens;
- rejeita `order_item_id` duplicado;
- materializa exatamente `quantity` unidades;
- preserva pedido, item, produto, nome opcional, dimensões originais, peso, flags físicas e sequência de entrega;
- retorna uma tupla e não altera a sequência recebida.

`CONFIRMADO`: conforme `ADR-005`, `expand_order_items` atribui `volume_index` de `1` a `quantity` para cada item, sem opção de base alternativa.

`CONFIRMADO`: não existe tabela separada `volumes`; a persistência futura materializará cada unidade diretamente em `load_plan_items`.

## OC13 - ordenação determinística

`CONFIRMADO`: `ordering.py` recebe uma sequência de volumes individuais e retorna uma nova tupla pela ordem total aprovada em `ADR-006`:

1. `volume_cm3` decrescente;
2. `weight_kg` decrescente;
3. não empilhável primeiro;
4. não frágil primeiro;
5. `delivery_sequence` decrescente;
6. valor inteiro não assinado do UUID de `order_item_id` crescente;
7. `volume_index` crescente.

`CONFIRMADO`: coleções não ordenadas, elementos com contrato incorreto e identidades duplicadas são rejeitados. A entrada não é alterada.

## OC14 - rotações ortogonais

`CONFIRMADO`: `rotations.py` gera orientações na ordem `XYZ`, `XZY`, `YXZ`, `YZX`, `ZXY`, `ZYX`, em que o código informa quais eixos originais ocupam os eixos usados `x`, `y` e `z`.

`CONFIRMADO`: cada orientação registra `rotation_code`, `used_width_cm`, `used_height_cm` e `used_length_cm`.

`CONFIRMADO`: `rotation_allowed = false` preserva somente `XYZ`. Orientações com dimensões usadas iguais são deduplicadas e mantêm o primeiro código da prioridade oficial, conforme `ADR-007`.

## OC15 - posicionamento first-fit provisório

`CONFIRMADO`: `placement.py` gera a origem `(0, 0, 0)` e as origens das três faces positivas de cada `PositionedAABB`: `(x + width, y, z)`, `(x, y + height, z)` e `(x, y, z + length)`. Coordenadas iguais são deduplicadas.

`CONFIRMADO`: `select_first_valid_candidate` percorre as combinações pela chave `(y, z, x, rotation_rank)` e retorna a primeira que passa pelos limites internos e por `validate_candidate`. O rank das rotações segue a `ADR-007`.

`CONFIRMADO`: `validate_candidate` é obrigatório, não possui default permissivo e só é chamado depois que o candidato passa por `fits_within_bounds`. O callback recebe um `PlacementCandidate` com o volume, a rotação e a caixa AABB.

`CONFIRMADO`: quando nenhuma rotação cabe nas dimensões internas, a busca usa `TRUCK_DIMENSIONS_EXCEEDED`. Quando há rotação dimensionalmente viável, mas nenhuma combinação é aceita, usa o fallback `NO_VALID_POSITION`.

`RISCO IDENTIFICADO`: `PlacementCandidate` representa somente um candidato provisório. A OC15 delega colisão ao validador da OC16 e apoio, empilhamento e fragilidade ao validador da OC17; mesmo com essas políticas, o resultado não pode ser publicado antes da composição do peso, do motivo final e da revalidação física integrada.

## OC16 - colisão AABB

`CONFIRMADO`: `geometry.py` valida dimensões positivas, coordenadas não negativas e os limites exatos dos três eixos. Também classifica duas caixas como `SEPARATED`, `TOUCHING` ou `POSITIVE_OVERLAP`.

`CONFIRMADO`: as primitivas e os futuros campos persistidos de dimensão e coordenada usam inteiros em centímetros, conforme as ADRs 002 e 008 e `docs/03-modelo-dados.md`.

`CONFIRMADO`: conforme a `ADR-009`, somente `POSITIVE_OVERLAP`, com extensão estritamente positiva nos eixos `x`, `y` e `z`, é colisão. `TOUCHING` por face, aresta ou vértice é permitido e a tolerância geométrica é zero.

`CONFIRMADO`: `is_collision_free(candidate_box, placed_boxes)` aceita o candidato apenas quando nenhuma caixa da sequência já posicionada possui sobreposição positiva com ele. A decisão não depende da ordem dessas caixas.

`CONFIRMADO`: a OC16 não implementa apoio, empilhamento, fragilidade, engine, persistência ou API. `COLLISION` integra o catálogo aprovado na OC18, mas o validador permanece booleano e seu mapeamento para o motivo final pertence à engine.

## OC17 - apoio, empilhamento e fragilidade

`CONFIRMADO`: conforme a `ADR-010`, `support.py` considera integralmente apoiado o volume no piso, em `y = 0`. Acima do piso, um suporte direto exige que seu topo coincida exatamente com a base do volume apoiado e que haja sobreposição com extensão positiva nos eixos `x` e `z`.

`CONFIRMADO`: a área apoiada é a união geométrica exata dos retângulos de contato de todos os suportes diretos. Regiões sobrepostas são contadas uma única vez, e a união deve cobrir 100% da base, sem tolerância, arredondamento ou apoio parcial.

`CONFIRMADO`: toda aresta de apoio transmite carga positiva por todos os ramos até os ancestrais. Cada suporte direto deve ter `stackable = true`, e nenhum suporte direto ou ancestral que receba carga pode ter `fragile = true`.

`CONFIRMADO`: um candidato `fragile` ou `stackable = false` pode ficar no topo quando nenhum volume acima transmite carga para ele. Não existe conceito nem limite de volume "pesado" para a regra de fragilidade.

`CONFIRMADO`: a API pura é formada por `SupportAssessment`, `analyze_support_configuration`, `is_support_configuration_valid` e `is_candidate_support_valid`. Ela valida a configuração completa para que um novo candidato também não torne inválidos volumes já posicionados.

`CONFIRMADO`: a OC17 não implementa engine, API HTTP ou persistência. Seus motivos estruturais integram o catálogo aprovado na OC18, mas o mapeamento do resultado booleano para o motivo final pertence à engine.

## OC18 - controle de peso isolado

`CONFIRMADO`: `weight.py` calcula o próximo peso com `Decimal`, aceita igualdade ao máximo e levanta exceção de domínio quando o candidato excede a capacidade, sem mutar o peso atual.

`CONFIRMADO`: excesso usa `TRUCK_WEIGHT_EXCEEDED`; entrada inválida usa `INVALID_WEIGHT_INPUT` e aborta o cálculo em vez de rejeitar um volume. O acumulado só deve ser substituído pelo valor retornado em uma tentativa aceita, garantindo que apenas volumes colocados componham o total.

`CONFIRMADO`: `rejections.py` define o catálogo e a precedência total da `ADR-011`. `select_rejection_reason` escolhe o motivo de maior prioridade independentemente da ordem recebida e rejeita valores fora do catálogo.

## Gates para a engine

`CONFIRMADO`: ainda não há `engine.py` nem `algorithm_version`; a composição dos validadores ocorrerá somente após as implementações sequenciais de ocupação e carregamento.

`RECOMENDAÇÃO`: manter os validadores isolados até que ocupação, carregamento e composição da engine sejam implementados e cobertos por uma revalidação final independente de todos os itens posicionados.
