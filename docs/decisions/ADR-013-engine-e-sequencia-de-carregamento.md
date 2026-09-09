# ADR-013: engine integrada e sequência de carregamento

Status: aceita

## Contexto

A OC20 precisa compor as regras puras das OC11 a OC19, definir a profundidade em
relação à porta e transformar apoios físicos e ordem de entrega em uma sequência
de carregamento determinística. A prioridade de tentativa da ADR-006 e o
first-fit da ADR-008 permanecem válidos e não podem ser substituídos por ordem
incidental ou backtracking implícito.

## Decisão

- A porta ocupa o plano `z = internal_length_cm`.
- A distância de um volume até a porta é medida entre sua face voltada à porta e
  esse plano: `internal_length_cm - (position_z_cm + used_length_cm)`.
- Para dois volumes com sequências de entrega diferentes, o de maior
  `delivery_sequence` deve ter distância até a porta maior ou igual. A igualdade
  permite volumes lado a lado na mesma faixa de profundidade.
- A restrição de profundidade integra o callback obrigatório do first-fit. Ela não
  altera a chave da ADR-006 nem a ordem de pontos e rotações da ADR-008.
- Apoio direto forma uma aresta do suporte para o volume apoiado. A
  `loading_sequence` é uma ordenação topológica de Kahn dessas arestas, iniciada
  em `1`, sem lacunas e com suportes sempre anteriores ao volume apoiado.
- Entre volumes disponíveis no mesmo passo topológico, a chave é:
  `delivery_sequence` decrescente, distância até a porta decrescente,
  `order_item_id` crescente pelo valor inteiro do UUID e `volume_index`
  crescente.
- A engine expande no máximo 200 volumes por execução síncrona. Exceder esse
  limite é erro de entrada e não uma rejeição individual.
- A precedência universal começa por dimensão e peso. Na busca espacial, o motivo
  descreve o estágio mais avançado alcançado: sem candidato livre de colisão,
  `COLLISION`; com candidato livre de colisão, mas estruturalmente inválido, o
  motivo estrutural de maior precedência; com candidato estruturalmente válido
  bloqueado apenas por profundidade, `NO_VALID_POSITION`.
- Ao final, a engine revalida de forma independente partição de identidades,
  limites, colisões, apoio, peso, profundidade, dependências e continuidade da
  sequência. Falha nessa etapa é erro interno de invariante, nunca plano parcial
  silencioso.
- A versão integrada inicial permanece `heuristic-v1`, já reservada pela
  ADR-012 para este conjunto determinístico de regras.

## Consequências

- O mesmo input produz as mesmas posições, rejeições, métricas e sequência.
- A heurística continua gulosa. Um volume priorizado antes pode ocupar uma faixa
  profunda e fazer uma entrega posterior receber `NO_VALID_POSITION`, mesmo que
  um rearranjo com backtracking existisse.
- A IA e o frontend não participam da validade física nem da sequência.
