# ADR-005: materialização e identidade de volumes individuais

Status: aceita

## Contexto

Cada `order_item` informa uma quantidade, mas o otimizador precisa tratar cada unidade como um volume individual, reproduzível e identificável. A documentação ainda mantinha abertas a criação de uma tabela `volumes` e a base zero ou um de `volume_index`.

## Decisão

- Não haverá tabela separada `volumes` no MVP.
- O núcleo expande `order_items.quantity` em memória antes da otimização.
- `volume_index` começa em `1` e termina em `quantity` para cada item.
- A identidade lógica de uma unidade é `(order_item_id, volume_index)`.
- Quando a persistência do plano for implementada, cada unidade será armazenada em `load_plan_items`, com unicidade por `(load_plan_id, order_item_id, volume_index)`.

## Consequências

- A expansão deixa de aceitar uma política configurável de base zero ou um.
- Banco, API, visualização e testes devem preservar a identidade 1-based.
- `order_items.quantity` continua sendo a fonte da quantidade antes do planejamento.
- A migration de `load_plan_items` será criada junto da integração de persistência, não nesta ocorrência de núcleo puro.
