# ADR-017: minimização de dados pessoais e paginação

Status: aceita

## Contexto

Os endpoints de coleção de usuários, clientes, motoristas, caminhões, produtos e
pedidos retornavam todas as linhas sem limite. As listagens de usuários,
clientes, motoristas e pedidos também reutilizavam os schemas detalhados e, por
isso, expunham dados pessoais que não são necessários para selecionar ou
identificar um registro na operação.

Além do risco de exposição excessiva, carregar uma tabela inteira torna o custo
de uma requisição proporcional ao crescimento da base. D12 precisava definir um
contrato único antes da implementação da OC59.

## Decisão

- Toda coleção atualmente implementada usa paginação 1-based por `page` e
  `page_size`. Os defaults são `1` e `20`; `page_size` aceita de `1` a `100`.
- A resposta usa o envelope `items`, `page`, `page_size`, `total` e
  `total_pages`. Uma página válida além do fim retorna `items` vazio e preserva
  os metadados; coleção vazia retorna `total_pages = 0`.
- `sort_order` aceita somente `asc` ou `desc`, com default `desc`. A ordenação é
  sempre por `created_at` e usa `id` como desempate determinístico na mesma
  direção.
- A OC59 não adiciona `sort_by`, busca livre ou filtros por dados pessoais.
  Filtros futuros exigem whitelist documentada e não podem permitir enumeração
  por e-mail, documento, telefone, CNH ou endereço.
- A paginação é executada no banco por `COUNT`, `LIMIT` e `OFFSET`; não é
  permitido carregar a tabela completa para recortá-la em memória.
- Listagens omitem, em vez de mascarar, campos que não são necessários:
  - usuários: `id`, `name`, `role`, `active`, `created_at`;
  - clientes: `id`, `name`, `city`, `state`, `created_at`;
  - motoristas: `id`, `name`, `license_category`, `active`, `created_at`;
  - pedidos: `id`, `customer_id`, `status`, `priority`,
    `expected_delivery_at`, `created_at`, `item_count`.
- Caminhões e produtos não contêm dados pessoais nos schemas atuais e mantêm os
  campos de leitura existentes dentro do envelope paginado.
- Endpoints de detalhe e respostas de escrita mantêm seus schemas completos,
  protegidos pela matriz RBAC da ADR-004. `password_hash` continua proibido em
  qualquer resposta.

## Consequências

- Consumidores de coleções precisam ler `items` e os metadados em vez de um
  array na raiz.
- E-mail, documento, telefone, número de CNH, endereços, observações e itens
  completos de pedido deixam de circular nas listagens.
- A omissão produz um contrato único por recurso e evita que valores mascarados
  ainda funcionem como sinal de enumeração.
- Novas coleções devem adotar o mesmo contrato ou registrar uma decisão que
  justifique a divergência.
