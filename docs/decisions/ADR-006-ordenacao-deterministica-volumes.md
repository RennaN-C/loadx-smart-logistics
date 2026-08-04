# ADR-006: ordenação determinística dos volumes

Status: aceita

## Contexto

O resultado da heurística depende da ordem em que os volumes são avaliados. Critérios sem precedência total ou dependentes da ordem recebida fariam o mesmo conjunto de volumes produzir planos diferentes.

## Decisão

Antes do posicionamento, os volumes são ordenados pela chave lexicográfica total:

1. `volume_cm3` decrescente;
2. `weight_kg` decrescente;
3. não empilhável antes de empilhável;
4. não frágil antes de frágil;
5. `delivery_sequence` decrescente;
6. `order_item_id` crescente;
7. `volume_index` crescente.

Um valor maior de `delivery_sequence` representa entrega posterior em todo o plano. Valores repetidos são permitidos e resolvidos pela identidade estável. No desempate, `order_item_id` usa o valor inteiro não assinado do UUID. Identidades duplicadas na mesma entrada são inválidas.

## Consequências

- O mesmo conjunto de volumes produz a mesma ordem independentemente da ordem de entrada.
- A ordenação retorna nova tupla e não altera a coleção recebida.
- Esta ordem define a prioridade de tentativa no otimizador; ela não substitui as regras futuras de posição nem `loading_sequence`.
- Alterar qualquer componente ou precedência da chave exige nova `algorithm_version` quando a engine estiver integrada.
