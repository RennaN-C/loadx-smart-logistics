# ADR-011: controle de peso e precedência das rejeições

Status: aceita

## Contexto

A OC18 precisa formalizar o controle incremental de peso e um catálogo público
de rejeições antes que os validadores isolados sejam compostos pela engine. O
resultado deve ser determinístico mesmo quando mais de uma falha física puder
explicar a rejeição de um volume.

## Decisão

- Pesos usam `Decimal` finito em quilogramas. O peso máximo e o peso do candidato
  devem ser positivos, e o acumulado deve estar entre zero e o máximo, inclusive.
- O próximo total é `current_weight_kg + candidate_weight_kg`. A igualdade exata
  com o limite é aceita.
- Um total acima do limite gera `TRUCK_WEIGHT_EXCEEDED`. A tentativa não altera o
  acumulado recebido; somente o retorno de uma tentativa aceita pode substituir o
  total da orquestração. Assim, apenas volumes efetivamente colocados compõem o
  peso total.
- O catálogo de `rejection_reason`, da maior para a menor precedência, é:
  `TRUCK_DIMENSIONS_EXCEEDED`, `TRUCK_WEIGHT_EXCEEDED`,
  `NON_STACKABLE_SUPPORT`, `FRAGILE_SUPPORT_WEIGHT_EXCEEDED`,
  `INSUFFICIENT_SUPPORT`, `COLLISION` e `NO_VALID_POSITION`.
- Quando houver mais de uma falha aplicável, o motivo final é sempre o primeiro
  deles na precedência aprovada, independentemente da ordem de descoberta.
- `NO_VALID_POSITION` é o fallback de menor precedência quando nenhuma regra
  física mais específica explicar a impossibilidade de posicionamento.
- Entrada inválida gera erro de domínio e, na futura fronteira HTTP, erro de API.
  Códigos `INVALID_*` não pertencem ao catálogo e nunca representam um volume
  rejeitado.
- A OC18 mantém peso, catálogo e precedência no núcleo puro. A composição com os
  demais validadores, a persistência e a API pertencem à engine integrada.

## Consequências

- A seleção do motivo é reproduzível e não depende da ordem incidental dos
  candidatos ou validadores.
- Exceções de peso e de posicionamento reutilizam valores do catálogo, evitando
  divergência entre o núcleo e o futuro contrato público.
- Persistência, schemas e respostas HTTP deverão aceitar somente os sete motivos
  aprovados para volumes rejeitados.
- Alterar aritmética de peso, catálogo ou precedência exigirá nova
  `algorithm_version` depois da integração da engine.
