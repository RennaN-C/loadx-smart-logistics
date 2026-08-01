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

`PENDENTE DE DEFINIÇÃO`: a equipe ainda deve decidir se `volume_index` começa em zero ou um.

`SUPOSIÇÃO TÉCNICA`: enquanto essa decisão não existe, `expand_order_items` exige explicitamente `VolumeIndexBase.ZERO` ou `VolumeIndexBase.ONE`, sem default. As duas alternativas existem somente para manter a mecânica testável; não são uma configuração de negócio aprovada. Engine, persistência e `algorithm_version` não podem escolher uma delas silenciosamente.

`DECISÃO NECESSÁRIA`: a expansão pura em memória não decide entre uma tabela `volumes` e a materialização direta em `load_plan_items`.

## OC16 - primitivas geométricas parciais

`CONFIRMADO`: `geometry.py` valida dimensões positivas, coordenadas não negativas e os limites exatos dos três eixos. Também classifica duas caixas como `SEPARATED`, `TOUCHING` ou `POSITIVE_OVERLAP`.

`SUPOSIÇÃO TÉCNICA`: essas primitivas usam inteiros em centímetros, coerentes com os models atuais e com a ADR-002. Isso não define a precisão futura dos campos persistidos.

`PENDENTE DE DEFINIÇÃO`: `TOUCHING` é somente uma classificação geométrica. A equipe ainda deve decidir se contato de face, aresta ou vértice conta como colisão e se haverá tolerância. Não existe validador final de colisão nem catálogo de rejeição.

## OC18 - controle de peso isolado

`CONFIRMADO`: `weight.py` calcula o próximo peso com `Decimal`, aceita igualdade ao máximo e levanta exceção de domínio quando o candidato excede a capacidade, sem mutar o peso atual.

`PENDENTE DE DEFINIÇÃO`: o código público de rejeição e sua precedência em relação a falhas geométricas/estruturais ainda não foram aprovados. Por isso, o validador não está integrado a uma engine.

## Gates para a engine

`DECISÃO NECESSÁRIA`: não há `engine.py` nem `algorithm_version` enquanto as decisões de ordenação, rotação, posicionamento, contato, apoio, fragilidade, ocupação, rejeições e sequência de carregamento estiverem abertas.

`RECOMENDAÇÃO`: integrar as primitivas somente depois que essas regras forem aprovadas e cobertas por uma revalidação final independente de todos os itens posicionados.
