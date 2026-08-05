# ADR-012: ocupação percentual determinística

Status: aceita

## Contexto

A OC19 precisa calcular aproveitamento, peso e contagens sem confundir o volume
físico dos produtos com o espaço interno vazio. O cálculo deve preservar precisão
decimal, ser independente da ordem das coleções e identificar a versão das regras
determinísticas usadas pelo planejamento.

## Decisão

- `used_volume_cm3` é a soma dos `volume_cm3` somente dos volumes colocados.
  Volumes rejeitados não contribuem para volume usado nem peso total.
- A ocupação é
  `used_volume_cm3 / internal_volume_cm3 * 100`.
- Os inteiros em centímetros cúbicos são convertidos diretamente para `Decimal`;
  `float` não participa do cálculo.
- O percentual é arredondado uma única vez, depois da soma completa, para duas
  casas decimais com quantum `Decimal("0.01")` e `ROUND_HALF_UP`.
- Uma carga sem volumes colocados produz `0.00`; ocupação integral produz
  `100.00`. Volume colocado acima do volume interno é erro de domínio e nunca é
  limitado silenciosamente a 100%.
- `loaded_count` e `unloaded_count` são, respectivamente, as quantidades nas
  coleções explícitas de colocados e rejeitados. As identidades dessas coleções
  devem ser únicas e disjuntas.
- A versão inicial é `heuristic-v1`. Uma mudança de regra determinística que
  altere o resultado exige nova `algorithm_version`; refatoração equivalente não.
- A OC19 mantém o cálculo no núcleo puro. Engine, persistência e API permanecem
  fora desta ocorrência.

## Consequências

- A ordem incidental de colocados ou rejeitados não altera as métricas.
- O contexto decimal global não altera soma ou arredondamento do núcleo.
- A função isolada valida que colocados e rejeitados não se sobrepõem, mas a
  engine deverá comprovar que formam uma partição completa da entrada expandida.
- A representação de `Decimal` em JSON continua pertencendo à decisão de
  contrato registrada para a OC56; esta ADR não escolhe número ou string JSON.
