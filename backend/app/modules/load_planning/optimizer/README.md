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

`RISCO IDENTIFICADO`: `PlacementCandidate` representa somente um candidato provisório. A OC15 não implementa colisão, contato, apoio, empilhamento ou fragilidade, e o resultado não pode ser publicado antes da composição das validações das OC16 e OC17.

## OC16 - primitivas geométricas parciais

`CONFIRMADO`: `geometry.py` valida dimensões positivas, coordenadas não negativas e os limites exatos dos três eixos. Também classifica duas caixas como `SEPARATED`, `TOUCHING` ou `POSITIVE_OVERLAP`.

`CONFIRMADO`: as primitivas e os futuros campos persistidos de dimensão e coordenada usam inteiros em centímetros, conforme as ADRs 002 e 008 e `docs/03-modelo-dados.md`.

`PENDENTE DE DEFINIÇÃO`: `TOUCHING` é somente uma classificação geométrica. A equipe ainda deve decidir se contato de face, aresta ou vértice conta como colisão e se haverá tolerância. Não existe validador final de colisão nem catálogo de rejeição.

## OC18 - controle de peso isolado

`CONFIRMADO`: `weight.py` calcula o próximo peso com `Decimal`, aceita igualdade ao máximo e levanta exceção de domínio quando o candidato excede a capacidade, sem mutar o peso atual.

`PENDENTE DE DEFINIÇÃO`: o código público de rejeição e sua precedência em relação a falhas geométricas/estruturais ainda não foram aprovados. Por isso, o validador não está integrado a uma engine.

## Gates para a engine

`DECISÃO NECESSÁRIA`: não há `engine.py` nem `algorithm_version` enquanto as decisões de contato, apoio, fragilidade, ocupação, rejeições e sequência de carregamento estiverem abertas.

`RECOMENDAÇÃO`: integrar as primitivas somente depois que essas regras forem aprovadas e cobertas por uma revalidação final independente de todos os itens posicionados.
