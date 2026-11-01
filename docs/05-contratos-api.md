# Contratos iniciais da API

## OC87 — planejamento multi-caminhão

`CONFIRMADO`: `/api/v1/load-distributions` é aditivo; contrato completo, RBAC,
necessidade, partição, estados, aprovação e reprocessamento estão em
[load_planning/distributions](../backend/app/modules/load_planning/distributions.md).
`RECOMENDAÇÃO`: decisões na [ADR-028](decisions/ADR-028-planejamento-multi-caminhao.md).
Planos legados e suas visualizações preservam schemas e endpoints. A liberação
operacional de múltiplas partes depende da OC90; uma só parte usa o fluxo atual.


## OC88 — otimização automática multi-caminhão

`CONFIRMADO`: `POST /api/v1/load-distributions/optimize` é operação protegida
para `ADMIN` e `LOGISTICS_MANAGER`; `CHECKER` e `DRIVER` não podem criar
propostas automáticas. O endpoint recebe
`DistributionNeedRequest` (`order_ids`). Em sucesso retorna `201` com
`DistributionRead`, persistido pelo mesmo agregado multi-caminhão da OC87.

A seleção tenta uma solução completa com menor quantidade de caminhões antes
de ampliar a frota. Somente caminhões elegíveis do preflight participam da
busca. O resultado físico de cada subconjunto é calculado pela engine
`heuristic-v1`; não existe segunda implementação de peso, dimensões, rotação,
colisão ou apoio.

Frota insuficiente retorna `422 DISTRIBUTION_CAPACITY_INSUFFICIENT` e não
persiste distribuição ou `LoadPlan` parcial. O detalhe informa volumes
restantes, motivos observados, frota inelegível e número de avaliações da
engine. Os contratos manuais da OC87 permanecem compatíveis.

## Evidências de entrega — OC80

`CONFIRMADO`: contrato aditivo `/api/v1/deliveries/{delivery_id}/evidences`:
POST event_id/kind/content_base64; GET metadata paginada; GET `/{evidence_id}`;
GET `/{evidence_id}/content` privado; POST `/{evidence_id}/revoke` com `{}`.
Somente DELIVERED com comprovante válido recebe PHOTO/SIGNATURE PNG/JPEG.
Schema OC78 e sessão/Origin/CSRF/RBAC são preservados. Contratos para OC81/OC83,
limites, códigos e idempotência no
[contrato de evidências](../backend/app/modules/deliveries/evidences.md).
`PENDENTE DE DEFINIÇÃO`: ativação de produção após política de storage/retenção
aprovada; ver [ADR-027 proposta](decisions/ADR-027-evidencias-de-entrega.md).

Este documento é o contrato combinado entre backend, frontend, algoritmo e integrações. Alterações devem ser discutidas, versionadas e refletidas em testes.

## Convenções

- `CONFIRMADO`: prefixo oficial da API de negócio: `/api/v1`.
- `CONFIRMADO`: os endpoints operacionais `/health` e `/ready` ficam fora do
  prefixo de negócio.
- `CONFIRMADO`: JSON usa campos em snake_case.
- `CONFIRMADO` por D06 e `ADR-016`: campos decimais públicos usam número JSON
  na entrada e na saída. Strings numéricas e booleanos são inválidos. O backend
  preserva `Decimal` internamente e cada campo mantém a precisão e escala do
  modelo aprovado; zeros finais não fazem parte do valor JSON.
- `RECOMENDAÇÃO`: caminhos usam kebab-case quando tiverem mais de uma palavra, como `/load-plans`.
- `CONFIRMADO` por D12 e `ADR-017`: coleções usam `page` 1-based (default `1`),
  `page_size` (default `20`, mínimo `1`, máximo `100`) e `sort_order`
  (`asc` ou `desc`, default `desc`). A ordenação é por `created_at`, com `id`
  como desempate na mesma direção.
- `CONFIRMADO`: coleções retornam `items`, `page`, `page_size`, `total` e
  `total_pages`. Página além do fim retorna `items` vazio; coleção vazia retorna
  `total_pages = 0`.
- `CONFIRMADO`: não há `sort_by`, busca livre ou filtros por dados pessoais na
  OC59. Todo filtro futuro usa query param em snake_case e whitelist documentada.
- `CONFIRMADO`: em atualizações parciais, campos omitidos permanecem inalterados; `null` só é aceito para campos anuláveis no modelo de dados.

### Evolução OC95 — busca e filtros de coleção

`CONFIRMADO`: OC95 sucede OC59 sem revogar a ADR-017. A whitelist abaixo é
aplicada no PostgreSQL antes de COUNT/OFFSET/LIMIT; `total` e `total_pages`
representam a coleção filtrada. Paginação 1-based, limites, envelope,
`sort_order`, desempate por `created_at, id`, RBAC e schemas são preservados.

| Endpoint GET `/api/v1` | `search` (campos permitidos) | Outros filtros |
| --- | --- | --- |
| `/orders` | ADMIN/LOGISTICS_MANAGER: nome do cliente e UUIDs do pedido/cliente; CHECKER: somente UUIDs do pedido/cliente | `status`: DRAFT, READY, PLANNED, IN_TRANSIT, DELIVERED, CANCELED |
| `/trucks` | plate, model | `archive_status` existente |
| `/products` | code, name | `restriction`: restricted ou free; `archive_status` existente |
| `/customers` | name, city | `archive_status` existente |
| `/drivers` | name | `archive_status` existente |

`search` é opcional, recebe trim no servidor e vazio/whitespace equivale à
ausência. Limite: 120 caracteres após trim; excesso retorna 422 no envelope
padrão. Busca substring case-insensitive parametrizada, com `%`, `_` e `\`
literais. Filtros diferentes combinam por AND; campos da busca combinam por OR.
Status inválido e restriction inválida retornam 422. Ausência de status ou
restriction inclui todos os valores. Não existe `priority`, busca por e-mail,
documento, telefone, CNH, endereço, notes ou qualquer outro campo pessoal.

`restricted` significa fragile=true OR stackable=false OR rotation_allowed=false;
`free` significa fragile=false AND stackable=true AND rotation_allowed=true.
A busca de pedidos por nome é exclusiva de ADMIN e LOGISTICS_MANAGER e usa
consulta de nomes pertencente a customers, sem carregar clientes em memória
nem duplicar pedidos/total. CHECKER mantém 200 na listagem, mas busca somente
UUID do pedido e UUID do cliente: termo que só corresponde ao nome retorna
coleção filtrada vazia. Nenhuma subconsulta de nome é construída para CHECKER;
DRIVER continua 403. A capacidade vem do papel autenticado, nunca de query param.
O RBAC dos endpoints é preservado, evitando que pedidos sejam um canal indireto
de consulta de nomes por quem não pode ler clientes. Não acrescenta nome ou dados
pessoais ao resumo. UUID é a referência identificadora já existente; nenhum
novo campo de referência foi criado.

`RISCO IDENTIFICADO`: available/unavailable de `/trucks/operational-status`
permanece fora desta whitelist. A fronteira FleetAvailabilityService calcula
disponibilidade individualmente após paginar. Aplicar filtro antes da paginação
exige evolução arquitetural que reutilize OC64/OC67/OC100/OC101 sem carregar toda
a frota nem duplicar regras. A UI mantém o aviso de filtro/contadores por página.

## Autenticação

Endpoint público de negócio:

- `POST /auth/login`.

Endpoints públicos operacionais:

- `GET /health`.
- `GET /ready`.

Endpoint disponível para qualquer usuário autenticado:

- `GET /auth/me`.
- `POST /auth/logout`.

Exemplo de login:

```json
{
  "email": "admin@example.test",
  "password": "senha-local"
}
```

Resposta `200`: o mesmo contrato `UserRead` usado por `/auth/me`.

```json
{
  "id": "uuid",
  "name": "Admin Local",
  "email": "admin@example.test",
  "role": "ADMIN",
  "driver_id": null,
  "active": true,
  "created_at": "2026-08-08T12:00:00Z"
}
```

O login envia o identificador somente em cookie. Em produção:

```text
Set-Cookie: __Host-loadx_session=<opaque>; Path=/; Secure; HttpOnly; SameSite=Lax
```

`CONFIRMADO` por D18 e `ADR-020`: o cookie não usa `Domain`, contém pelo menos
256 bits aleatórios e somente seu hash é persistido. No ambiente local HTTP, o
nome é `loadx_session` e `Secure` fica desabilitado; o prefixo `__Host-` nunca é
emitido com atributos incompatíveis.

`POST /auth/login` e `GET /auth/me` retornam também `X-CSRF-Token` no header. O
frontend mantém esse valor somente em memória e o envia em todo `POST`, `PUT`,
`PATCH` ou `DELETE` autenticado:

```text
X-CSRF-Token: <session-bound-token>
```

`POST /auth/logout` exige cookie, `Origin` e `X-CSRF-Token`, retorna `204`, revoga
a sessão atual e expira o cookie.

Erros específicos:

- `AUTH_INVALID_CREDENTIALS`: e-mail ou senha inválidos.
- `AUTH_INVALID_TOKEN`: sessão ausente, inválida, revogada, expirada ou usuário
  inexistente.
- `AUTH_USER_INACTIVE`: usuário inativo.
- `AUTH_FORBIDDEN`: usuário autenticado sem permissão para a ação.
- `AUTH_RATE_LIMITED`: login temporariamente limitado; usa `429` e
  `Retry-After` inteiro em segundos.
- `AUTH_ORIGIN_FORBIDDEN`: método inseguro sem origem aprovada.
- `AUTH_CSRF_INVALID`: token CSRF ausente ou inválido.

`CONFIRMADO`: `POST /auth/register` foi removido do contrato por `D03` e `ADR-004`. O primeiro `ADMIN` é criado por comando administrativo local; os usuários seguintes são criados por `ADMIN` em `POST /users`.

`CONFIRMADO`: depois das migrations e antes de expor a API, o bootstrap é executado em `backend` com `python -m app.modules.auth.bootstrap` ou, pela raiz, com `docker compose run --rm backend python -m app.modules.auth.bootstrap`. A senha é lida de forma oculta e o comando recusa execução quando já existe qualquer usuário.

`CONFIRMADO`: ausência ou invalidade de autenticação retorna `401
AUTH_INVALID_TOKEN`; autenticação válida sem permissão retorna `403
AUTH_FORBIDDEN`.

`CONFIRMADO`: após a `OC51-G`, todos os endpoints de negócio atualmente implementados exigem autenticação e aplicam a matriz aprovada.

`CONFIRMADO` por D18 e `ADR-020`: não existe refresh token. A sessão expira após
30 minutos de inatividade ou 8 horas absolutas. Login é limitado por conta e IP
com atrasos de 1, 5, 15 e 60 minutos a partir da quinta falha. Conta inexistente,
senha inválida e usuário inativo retornam `401 AUTH_INVALID_CREDENTIALS` sem
revelar qual condição ocorreu.

## Saúde

### GET `/health`

```json
{
  "status": "ok",
  "service": "loadx-api"
}
```

`CONFIRMADO`: `/health` é liveness e não consulta PostgreSQL ou Alembic.

### GET `/ready`

Resposta `200` quando PostgreSQL está acessível e `alembic_version` corresponde
exatamente aos heads entregues com a aplicação:

```json
{
  "status": "ready",
  "service": "loadx-api"
}
```

Resposta `503` para banco indisponível, timeout, tabela de versão ausente ou
revisão divergente:

```json
{
  "code": "SERVICE_NOT_READY",
  "message": "O serviço não está pronto.",
  "details": []
}
```

`CONFIRMADO` por D11 e `ADR-018`: a verificação é somente leitura, não aplica
migrations, possui orçamento total de 2 segundos e não expõe componente, URL,
credencial, revisão, exceção ou stack trace.

## Usuários

- `GET /users`.
- `POST /users`.
- `GET /users/{id}`.
- `PATCH /users/{id}`.

Regras do contrato aprovado:

- Todas as rotas de `/users` exigem perfil `ADMIN`.
- A listagem retorna somente `id`, `name`, `role`, `active` e `created_at`.
- Detalhe e respostas de escrita retornam `id`, `name`, `email`, `role`,
  `driver_id`, `active` e `created_at`.
- `password_hash` nunca é retornado.
- `role` aceita `ADMIN`, `CHECKER`, `DRIVER` e `LOGISTICS_MANAGER`.
- `email` é normalizado para minúsculas.
- `role` é normalizado para maiúsculas.
- `driver_id` é opcional; valor não nulo exige `role = DRIVER`, motorista
  existente e vínculo não utilizado por outro usuário.
- Alterar `driver_id` revoga todas as sessões do usuário na mesma transação.
- `password` deve ter entre 15 e 128 caracteres na entrada, aceita espaços e
  Unicode e não exige composição artificial.

Erros específicos:

- `USER_NOT_FOUND`: usuário não encontrado.
- `USER_EMAIL_ALREADY_EXISTS`: e-mail já cadastrado.
- `USER_LAST_ACTIVE_ADMIN_REQUIRED`: alteração deixaria o sistema sem `ADMIN` ativo.
- `USER_DRIVER_NOT_FOUND`: `driver_id` não referencia motorista existente.
- `USER_DRIVER_ALREADY_LINKED`: motorista já está vinculado a outro usuário.
- `USER_DRIVER_ROLE_REQUIRED`: vínculo foi informado para papel diferente de
  `DRIVER`.

`CONFIRMADO`: não existe cadastro público. O primeiro `ADMIN` usa bootstrap local e, depois, usuários são criados somente por `ADMIN`.

## Caminhões

- `GET /trucks`.
- `POST /trucks`.
- `GET /trucks/{id}`.
- `PATCH /trucks/{id}`.

Regras de autorização:

- `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem usar `GET`.
- `ADMIN` e `LOGISTICS_MANAGER` podem usar `POST` e `PATCH`.
- `DRIVER` não acessa essas rotas na API atual.

Exemplo de criação:

```json
{
  "plate": "ABC1D23",
  "model": "Bau medio",
  "internal_width_cm": 240,
  "internal_height_cm": 260,
  "internal_length_cm": 600,
  "max_weight_kg": 8000
}
```

`RECOMENDAÇÃO`: exclusão deve ser lógica por `active = false` até a equipe aprovar regra de delete físico.

## Produtos

- `GET /products`.
- `POST /products`.
- `GET /products/{id}`.
- `PATCH /products/{id}`.

Regras de autorização:

- `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem usar `GET`.
- `ADMIN` e `LOGISTICS_MANAGER` podem usar `POST` e `PATCH`.
- `DRIVER` não acessa essas rotas na API atual.

Exemplo de criação:

```json
{
  "code": "CX-A",
  "name": "Caixa A",
  "description": "Produto de demonstracao",
  "width_cm": 60,
  "height_cm": 50,
  "length_cm": 40,
  "weight_kg": 12.5,
  "fragile": false,
  "stackable": true,
  "rotation_allowed": true
}
```

## Clientes

- `GET /customers`.
- `POST /customers`.
- `GET /customers/{id}`.
- `PATCH /customers/{id}`.

Regras de autorização:

- `ADMIN` e `LOGISTICS_MANAGER` podem usar `GET`.
- `ADMIN` e `LOGISTICS_MANAGER` podem usar `POST` e `PATCH`.
- `CHECKER` e `DRIVER` não acessam essas rotas.

Campos de `GET /customers`: `id`, `name`, `city`, `state` e `created_at`.
Documento, telefone, endereço e observações aparecem somente no detalhe e nas
respostas de escrita já protegidas pelo RBAC.

`CONFIRMADO` (OC63): `POST`/`PATCH` validam `document` como CPF de 11 dígitos ou
CNPJ numérico de 14 dígitos, aceitando as máscaras `XXX.XXX.XXX-XX` e
`XX.XXX.XXX/XXXX-XX`. Ambos verificadores devem ser válidos; letras, máscaras
incorretas e sequências repetidas são rejeitadas. `phone` continua opcional.
Campos novos/alterados são persistidos e retornados sem máscara.

### Consulta auxiliar de CEP — OC62

`CONFIRMADO` (v1.2.0): `GET /api/v1/customers/cep/{cep}` exige sessão e papel
`ADMIN` ou `LOGISTICS_MANAGER`. `CHECKER` e `DRIVER` não podem consultá-la.
A rota recebe somente CEP, normaliza oito dígitos com hífen opcional antes da
consulta e aplica timeout HTTP de 5 segundos por fase. O cadastro manual é
independente.

`CONFIRMADO`: resposta `200` usa `ViaCEPAddress`, com `cep`, `street`,
`neighborhood`, `complement`, `city` e `state`, sem envelope. CEP retorna oito
dígitos; rua, bairro e complemento são opcionais (`null`) e aceitam até 255
caracteres cada; cidade é obrigatória, de 1 a 120 caracteres; UF é uma sigla
brasileira válida de duas letras maiúsculas. Dados externos acima dos limites
são rejeitados. O endereço composto continua sujeito ao limite de Customer.

`CONFIRMADO`: os erros usam `ErrorResponse` (`code`, `message`, `details`):

| Status | Código | Condição |
| --- | --- | --- |
| `401` | `AUTH_INVALID_TOKEN` | Sessão ausente ou inválida. |
| `403` | `AUTH_FORBIDDEN` | Perfil sem acesso à consulta. |
| `422` | `VIACEP_INVALID_CEP` | Formato inválido; nenhuma consulta externa. |
| `404` | `VIACEP_NOT_FOUND` | CEP inexistente. |
| `503` | `VIACEP_UNAVAILABLE` | Serviço indisponível. |
| `504` | `VIACEP_TIMEOUT` | Timeout do serviço externo. |
| `502` | `VIACEP_INVALID_RESPONSE` | Resposta inválida, incompleta ou acima dos limites. |

`CONFIRMADO`: `VIACEP_INVALID_CEP` identifica `cep` em `details`; as falhas do
provider retornam `details: []` e mensagens normalizadas, sem detalhes internos.
Contrato, exemplo de sucesso e injeção de fake estão em
[ViaCEP — contrato público para a OC70](../backend/app/integrations/viacep/README.md).
O frontend deve consultar o backend, nunca o ViaCEP diretamente.

## Motoristas

- `GET /drivers`.
- `POST /drivers`.
- `GET /drivers/{id}`.
- `PATCH /drivers/{id}`.

Regras de autorização:

- `ADMIN` e `LOGISTICS_MANAGER` podem usar `GET`.
- `ADMIN` e `LOGISTICS_MANAGER` podem usar `POST` e `PATCH`.
- `CHECKER` e `DRIVER` não acessam essas rotas.

Campos de `GET /drivers`: `id`, `name`, `license_category`, `active` e
`created_at`. Documento, telefone e número da CNH aparecem somente no detalhe e
nas respostas de escrita já protegidas pelo RBAC.

`CONFIRMADO` (OC63): `POST`/`PATCH` validam `document` como CPF e
`license_number` como CNH de 11 dígitos, incluindo ambos os verificadores e
rejeição de sequências repetidas. CPF aceita máscara padrão; CNH, somente
dígitos. `phone` é obrigatório. Campos novos/alterados retornam sem máscara.

`CONFIRMADO`: nos dois cadastros, telefone aceita 10 ou 11 dígitos nacionais,
DDD não iniciado em 0 e celular iniciado em 9 após o DDD. Aceita DDD com ou
sem parênteses, espaço após DDD e hífen antes dos quatro últimos dígitos,
ambos opcionais. Código internacional e ramal não são aceitos. Entrada é
string; os formatos aceitam espaços nas extremidades e somente dígitos ASCII.

`CONFIRMADO`: PATCH mantém campos omitidos. `null` é aceito apenas no telefone
do cliente, entre os campos da OC63; string vazia não limpa o telefone.
Valor inválido retorna `422 VALIDATION_ERROR`, com o campo em `details`,
preservando o envelope atual. Leituras de registros legados não são revalidadas
nem corrigidas automaticamente nesta ocorrência.

## Pedidos

- `GET /orders`.
- `POST /orders`.
- `GET /orders/{id}`.
- `PATCH /orders/{id}`.
- `PATCH /orders/{id}/status`.

Regras de autorização:

- `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem usar `GET`.
- `ADMIN` e `LOGISTICS_MANAGER` podem usar `POST` e `PATCH`.
- `DRIVER` não acessa essas rotas na API atual; sua operação ocorre pelos
  endpoints da viagem atribuída.

Exemplo de criação:

```json
{
  "customer_id": "uuid",
  "priority": "NORMAL",
  "delivery_address": "Rua Exemplo, 100",
  "expected_delivery_at": "2026-08-10T13:00:00Z",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 3,
      "delivery_sequence": 1
    }
  ]
}
```

Regras atuais:

- `GET /orders` retorna `id`, `customer_id`, `status`, `priority`,
  `expected_delivery_at`, `created_at` e `item_count`; omite
  `delivery_address` e os itens completos.

- `POST /orders` cria o pedido com `status = "DRAFT"`.
- `PATCH /orders/{id}` aceita alteração de `customer_id`, `priority`,
  `delivery_address`, `expected_delivery_at` e, quando `items` for enviado,
  substitui o conjunto somente em `DRAFT` e se nenhum item estiver referenciado
  por plano. O payload rejeita `status` e campos desconhecidos.
- `PATCH /orders/{id}/status` recebe `{"status": "READY"}` e aplica somente a
  matriz de transições manuais de D04. Aprovação de plano, início de viagem e
  conclusão de entrega mantêm seus próprios casos de uso.
- `status` aceita `DRAFT`, `READY`, `PLANNED`, `IN_TRANSIT`, `DELIVERED` e `CANCELED`.
- `priority` aceita `LOW`, `NORMAL`, `HIGH` e `URGENT` e é normalizado para
  maiúsculas. Outro valor na criação ou atualização retorna o erro padronizado
  de validação com status `422`.
- `expected_delivery_at` deve vir com timezone e é normalizado para UTC.
- O pedido deve possuir pelo menos um item.
- `quantity` e `delivery_sequence` devem ser maiores que zero.
- Todos os itens do mesmo pedido devem usar a mesma `delivery_sequence` na
  OC09; pedidos diferentes podem compartilhar o valor e usam UUID como
  desempate determinístico.
- `customer_id` deve existir em `customers`.
- Todos os `product_id` dos itens devem existir em `products`.

Erros específicos:

- `ORDER_NOT_FOUND`: pedido não encontrado.
- `ORDER_CUSTOMER_NOT_FOUND`: cliente do pedido não encontrado.
- `ORDER_PRODUCT_NOT_FOUND`: produto do pedido não encontrado.
- `ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN`: conflito `409`; os itens históricos não
  podem ser substituídos.
- `ORDER_EDIT_NOT_ALLOWED`: conflito `409`; o pedido não está em `DRAFT`.
- `ORDER_STATUS_TRANSITION_NOT_ALLOWED`: conflito `409`; a origem e o destino
  não formam uma transição manual aprovada.

`CONFIRMADO`: criação e cada transição efetiva persistem pedido e histórico em
uma única transação. A criação registra `null -> DRAFT`; repetir o estado atual
retorna o pedido sem criar histórico duplicado.

## Hierarquia administrativa na v1.2.0

A hierarquia vigente autoriza ADMIN a executar as ações logísticas atribuídas
a LOGISTICS_MANAGER e as ações de conferência de CHECKER, além das funções
administrativas exclusivas de ADMIN. A ampliação exige sessão, Origin/CSRF,
autorização por recurso e todas as validações de domínio habituais.
LOGISTICS_MANAGER não administra usuários/identidade/permissões/configurações
institucionais. DRIVER permanece vinculado ao próprio motorista e não pode
ser personificado por ADMIN. A OC112 evoluirá a matriz fixa para catálogo de
permissões logísticas; esta mudança não cria direitos de plataforma CoreFlow.

## Planos de carga

Regras de autorização:

- `ADMIN` e `LOGISTICS_MANAGER` usam criação, comparação, aprovação e recálculo.
- `ADMIN` e `LOGISTICS_MANAGER` consultam e solicitam explicação de qualquer plano
  persistido tecnicamente válido.
- `CHECKER` consulta e solicita explicação somente de plano `APPROVED`.
- `DRIVER` não acessa os endpoints de plano de carga; a viagem usa internamente o
  plano atribuído.

### GET `/load-plans` — recuperação de planejamentos (#208)

`CONFIRMADO`: consulta somente leitura, paginada no PostgreSQL. Usa `page=1`,
`page_size=20` (1–100) e `sort_order=desc` (`asc`/`desc`). Ordena por
`created_at, id` na mesma direção. Filtros opcionais aprovados nesta manutenção:
`status` (`CALCULATED`, `APPROVED`, `REJECTED`) e `truck_id` UUID, aplicados antes
do COUNT/LIMIT/OFFSET. Não há busca livre, `sort_by` ou filtro por dados pessoais.

Envelope: `items`, `page`, `page_size`, `total`, `total_pages`. Cada item contém
`id`, `truck_id`, `truck_plate`, `truck_model`, `status`, `created_at`,
`recalculated_from_id`, `loaded_count`, `unloaded_count`, `occupancy_percent`,
`total_weight_kg`, `order_count`. Placa/modelo vêm do snapshot histórico, não do
cadastro atual. Não carrega entidades/coleções de volumes, coordenadas, pedidos
completos nem dados pessoais; contagem de pedidos é uma subconsulta agregada.

ADMIN e LOGISTICS_MANAGER consultam todos os planos. CHECKER recebe somente
APPROVED, inclusive no total e nas páginas; solicitar outro status retorna
coleção vazia. DRIVER recebe 403, sessão ausente 401, parâmetros inválidos 422.
Página além do fim retorna items vazio; nenhum GET calcula ou cria operação.

### GET `/load-plans/{id}/continuity`

`CONFIRMADO`: consulta contextual dos vínculos persistidos, sem central global
ou varredura de `GET /trips`. Retorna `loading_session: {id, status} | null`,
`trip: {id, status} | null` e `operational_ready: boolean`. Reutiliza interfaces
públicas dos módulos de carregamento/entrega e a fronteira operacional dos planos.
Inclui viagens finalizadas para preservar a recuperação histórica.

Mesma autorização do detalhe: ADMIN/LOGISTICS_MANAGER leem; CHECKER somente
APPROVED e recebe `trip=null`, pois não pode consultar viagens; DRIVER 403,
sessão ausente 401, plano inexistente 404, UUID inválido 422. `operational_ready`
exige plano aprovado e compatibilidade da distribuição com a operação atual;
não representa reserva ou garantia de disponibilidade. Escritas continuam
validando conflitos, identidade, aprovação, pedidos, motorista e documentação.
Uma viagem pode ser programada antes de concluir o carregamento, conforme
ADR-022; somente seu início exige carregamento FINISHED.

`CONFIRMADO`: vínculo único `uq_trips__load_plan_id` e lock do plano na criação
já protegem contra viagens duplicadas. A consulta não elimina a necessidade da
validação transacional. Falha ao consultar continuidade não significa ausência.
A UI não oferece criar enquanto os vínculos não forem confirmados; conflito
TRIP_LOAD_PLAN_ALREADY_ASSIGNED reconsulta a continuidade.

### POST `/load-plans`

```json
{
  "truck_id": "uuid",
  "order_ids": ["uuid"]
}
```

`order_ids` deve conter ao menos um UUID e não aceita duplicatas. O caminhão deve
estar ativo, todos os pedidos devem estar em `READY` e a soma das quantidades não
pode exceder 200 volumes.

Resposta `201`, também usada por `GET /load-plans/{id}`:

```json
{
  "id": "uuid",
  "truck_id": "uuid",
  "recalculated_from_id": null,
  "status": "CALCULATED",
  "internal_volume_cm3": 37440000,
  "used_volume_cm3": 32400000,
  "occupancy_percent": 86.54,
  "total_weight_kg": 5420.000,
  "loaded_count": 28,
  "unloaded_count": 0,
  "algorithm_version": "heuristic-v1",
  "created_at": "2026-08-04T12:00:00Z",
  "approved_at": null,
  "order_ids": ["uuid"],
  "items": [
    {
      "id": "load-plan-item-uuid",
      "order_id": "uuid",
      "order_item_id": "uuid",
      "product_id": "uuid",
      "volume_index": 1,
      "quantity": 1,
      "delivery_sequence": 2,
      "product_code": "CX-A",
      "product_name": "Caixa A",
      "original_width_cm": 60,
      "original_height_cm": 50,
      "original_length_cm": 40,
      "weight_kg": 12.500,
      "fragile": false,
      "stackable": true,
      "rotation_allowed": true,
      "x_cm": 0,
      "y_cm": 0,
      "z_cm": 0,
      "width_cm": 60,
      "height_cm": 50,
      "length_cm": 40,
      "rotation_code": "XYZ",
      "loading_sequence": 1,
      "placed": true,
      "rejection_reason": null
    }
  ]
}
```

Os campos físicos e descritivos de caminhão/produto/item são snapshots do momento
do cálculo. `Decimal` permanece no domínio, no schema interno e na persistência;
a fronteira HTTP usa número JSON conforme D06 e `ADR-016`.

### GET `/load-plans/{id}/visualization`

```json
{
  "truck": {
    "id": "uuid",
    "plate": "ABC1D23",
    "model": "Bau medio",
    "width_cm": 240,
    "height_cm": 260,
    "length_cm": 600,
    "max_weight_kg": 8000.00
  },
  "items": [
    {
      "id": "load-plan-item-uuid",
      "order_id": "uuid",
      "order_item_id": "uuid",
      "product_id": "uuid",
      "volume_index": 1,
      "quantity": 1,
      "delivery_sequence": 2,
      "product_code": "CX-A",
      "product_name": "Caixa A",
      "original_width_cm": 60,
      "original_height_cm": 50,
      "original_length_cm": 40,
      "weight_kg": 12.500,
      "fragile": false,
      "stackable": true,
      "rotation_allowed": true,
      "x_cm": 0,
      "y_cm": 0,
      "z_cm": 0,
      "width_cm": 60,
      "height_cm": 50,
      "length_cm": 40,
      "rotation_code": "XYZ",
      "loading_sequence": 1
    }
  ],
  "unloaded_items": [
    {
      "id": "load-plan-item-uuid",
      "order_id": "uuid",
      "order_item_id": "uuid",
      "product_id": "uuid",
      "volume_index": 1,
      "quantity": 1,
      "delivery_sequence": 1,
      "product_code": "CX-B",
      "product_name": "Caixa B",
      "original_width_cm": 300,
      "original_height_cm": 300,
      "original_length_cm": 300,
      "weight_kg": 20.000,
      "fragile": false,
      "stackable": true,
      "rotation_allowed": false,
      "rejection_reason": "TRUCK_DIMENSIONS_EXCEEDED"
    }
  ]
}
```

`CONFIRMADO`: `rejection_reason` aceita somente, em ordem de precedência, `TRUCK_DIMENSIONS_EXCEEDED`, `TRUCK_WEIGHT_EXCEEDED`, `NON_STACKABLE_SUPPORT`, `FRAGILE_SUPPORT_WEIGHT_EXCEEDED`, `INSUFFICIENT_SUPPORT`, `COLLISION` ou `NO_VALID_POSITION`. Entrada inválida gera erro de domínio/API e não aparece como volume rejeitado.

`CONFIRMADO`: conforme `ADR-007`, `rotation_code` usa somente `XYZ`, `XZY`, `YXZ`, `YZX`, `ZXY` ou `ZYX`. As letras indicam quais eixos originais `width`, `height` e `length` ocupam, respectivamente, as dimensões usadas em `x`, `y` e `z`.

### POST `/load-plans/{id}/approve`

Sem body. Retorna `200` com o mesmo `LoadPlanRead`. Exige plano `CALCULATED` sem
rejeições e muda plano/pedidos/histórico atomicamente; pedidos passam a `PLANNED`.

### POST `/load-plans/{id}/recalculate`

Sem body. Retorna `201`. Sempre cria outro plano com
`recalculated_from_id = id` da origem, reutiliza caminhão/pedidos, recarrega os
dados atuais e preserva a origem.

Erros específicos:

- `LOAD_PLAN_NOT_FOUND`.
- `LOAD_PLAN_TRUCK_NOT_FOUND` e `LOAD_PLAN_TRUCK_INACTIVE`.
- `LOAD_PLAN_ORDER_NOT_FOUND` e `LOAD_PLAN_ORDER_NOT_ELIGIBLE`.
- `LOAD_PLAN_PRODUCT_NOT_FOUND`.
- `LOAD_PLAN_VOLUME_LIMIT_EXCEEDED`.
- `INVALID_LOAD_PLAN_INPUT`.
- `LOAD_PLAN_INVALID_STATUS`, `LOAD_PLAN_HAS_REJECTIONS` e
  `LOAD_PLAN_SOURCE_CHANGED`.

### POST `/load-plans/compare-trucks`

Compara de forma transitória os mesmos pedidos em diferentes caminhões. Exige
`ADMIN` ou `LOGISTICS_MANAGER` e não persiste nem cria `LoadPlan`.

```json
{
  "order_ids": ["uuid-do-pedido"],
  "truck_ids": ["uuid-do-caminhao-a", "uuid-do-caminhao-b"]
}
```

Regras de entrada e preflight:

- `order_ids` contém ao menos um UUID e não aceita duplicatas;
- `truck_ids` contém de 2 a 10 UUIDs e não aceita duplicatas;
- todos os pedidos devem existir e estar elegíveis;
- todos os produtos referenciados devem existir;
- todos os caminhões devem existir e estar ativos;
- a soma das quantidades dos pedidos pode materializar no máximo 200 volumes;
- qualquer falha invalida a requisição inteira antes do primeiro cálculo.

Resposta `200`: array direto, com um elemento por caminhão na mesma ordem de
`truck_ids`.

```json
[
  {
    "truck_id": "uuid-do-caminhao-a",
    "internal_volume_cm3": 37440000,
    "used_volume_cm3": 32400000,
    "occupancy_percent": 86.54,
    "total_weight_kg": 5420.0,
    "loaded_count": 28,
    "unloaded_count": 0,
    "rejection_counts": {},
    "algorithm_version": "heuristic-v1"
  },
  {
    "truck_id": "uuid-do-caminhao-b",
    "internal_volume_cm3": 18000000,
    "used_volume_cm3": 15000000,
    "occupancy_percent": 83.33,
    "total_weight_kg": 4200.0,
    "loaded_count": 22,
    "unloaded_count": 6,
    "rejection_counts": {
      "TRUCK_DIMENSIONS_EXCEEDED": 4,
      "TRUCK_WEIGHT_EXCEEDED": 2
    },
    "algorithm_version": "heuristic-v1"
  }
]
```

`rejection_counts` usa os motivos oficiais de `rejection_reason` como chaves e
contagens inteiras positivas como valores; fica vazio quando nenhum volume é
rejeitado. Um caminhão ativo e válido que não comporte toda a carga continua no
array com suas métricas e rejeições. Isso não transforma a resposta em falha.

`CONFIRMADO`: a ordem do array serve somente para correlacionar cada elemento ao
pedido. A resposta não contém vencedor, score, ranking ou recomendação e não
altera a `heuristic-v1`.

Erros específicos:

- `VALIDATION_ERROR`: `order_ids` vazio ou duplicado, `truck_ids` duplicado ou
  com menos de 2 ou mais de 10 elementos, ou UUID malformado;
- `LOAD_PLAN_ORDER_NOT_FOUND` e `LOAD_PLAN_ORDER_NOT_ELIGIBLE`;
- `LOAD_PLAN_PRODUCT_NOT_FOUND`;
- `LOAD_PLAN_TRUCK_NOT_FOUND` e `LOAD_PLAN_TRUCK_INACTIVE`;
- `LOAD_PLAN_VOLUME_LIMIT_EXCEEDED`;
- `INVALID_LOAD_PLAN_INPUT`.

### POST `/load-plans/{id}/explain`

Sem body. Explica um plano persistido sem recalcular, aprovar ou modificar seus
dados. `LOGISTICS_MANAGER` e `ADMIN` podem consultar a explicação de qualquer
plano tecnicamente válido. `CHECKER` pode consultar somente plano `APPROVED` e
`DRIVER` não possui acesso.

Resposta `200` com provider disponível e resposta válida:

```json
{
  "load_plan_id": "uuid-do-plano",
  "source": "AI",
  "explanation": "O plano utilizou 86,54% do volume interno e carregou 28 volumes.",
  "algorithm_version": "heuristic-v1"
}
```

Quando o provider ultrapassa o timeout, está indisponível ou produz resposta
inválida, a mesma operação retorna `200` com explicação determinística e
`source = FALLBACK`. O timeout é configurável e usa 5 segundos por padrão.
`source` aceita exclusivamente `AI` ou `FALLBACK`; `algorithm_version` sempre vem
do plano persistido.

O contexto entregue ao `AIProvider` contém somente métricas, snapshot técnico do
caminhão, posições, rotações, sequência, volumes rejeitados, motivos e
`algorithm_version`. Não contém nome, CPF/CNPJ, telefone ou endereço de cliente,
nem dados pessoais de motorista.

O fallback não encobre erros de autenticação, autorização, recurso inexistente
ou plano tecnicamente inválido. Erros específicos:

- `AUTH_INVALID_TOKEN` ou `AUTH_FORBIDDEN`;
- `LOAD_PLAN_NOT_FOUND`;
- `LOAD_PLAN_EXPLANATION_INVALID_PLAN`: conflito `409`; o plano persistido não
  satisfaz os invariantes necessários para formar o contexto técnico;
- `VALIDATION_ERROR`: UUID de path malformado.

`CONFIRMADO`: o MVP usa uma implementação fake de `AIProvider`, sem rede ou
credencial externa. O adapter concreto será integrado pelo Desenvolvedor 4.

## Carregamento

- `POST /loading-sessions`.
- `GET /loading-sessions/{id}`.
- `PATCH /loading-sessions/{id}/status`.
- `PATCH /loading-sessions/{id}/items/{item_id}`.

`CONFIRMADO`: `POST` recebe `load_plan_id` e cria ou retorna a única sessão do
plano `APPROVED`. A sessão inicia `PENDING`; o status aceita somente
`IN_PROGRESS` e depois `FINISHED`. Cada item recebe `CHECKED` pelo endpoint de
item, e a finalização falha enquanto algum item estiver pendente.

`CONFIRMADO` (OC66): a autorização é definida por operação:

| Operação | Endpoint | `ADMIN` | `LOGISTICS_MANAGER` | `CHECKER` | `DRIVER` |
|---|---|---:|---:|---:|---:|
| Leitura | `GET /loading-sessions/{id}` | Sim | Sim | Sim | Não |
| Criação | `POST /loading-sessions` | Sim | Sim | Não | Não |
| Início da conferência | `PATCH /loading-sessions/{id}/status` com `IN_PROGRESS` | Sim | Não | Sim | Não |
| Conferência de item | `PATCH /loading-sessions/{id}/items/{item_id}` com `CHECKED` | Sim | Não | Sim | Não |
| Finalização | `PATCH /loading-sessions/{id}/status` com `FINISHED` | Sim | Não | Sim | Não |

`CONFIRMADO` (OC66): perfis negados recebem `403 AUTH_FORBIDDEN` antes de
qualquer consulta à sessão ou ao item; autenticação ausente ou inválida continua
recebendo `401 AUTH_INVALID_TOKEN`. Portanto, uma negativa de RBAC não revela se
os UUIDs solicitados existem.

`CONFIRMADO` (OC66): não existe autorização por objeto neste módulo. O modelo
atual não possui atribuição de sessão ou item a um `CHECKER`; criar esse vínculo
fica fora da OC66. Para OC75 e OC76, leitura de código deve apenas identificar um
item e reutilizar a operação de conferência protegida para `CHECKER`; código de
QR/barras não autentica, não autoriza e não amplia os perfis desta matriz.

Erros específicos:
`LOADING_PLAN_NOT_APPROVED`, `LOADING_SESSION_NOT_FOUND`,
`LOADING_ITEM_NOT_FOUND`, `LOADING_ITEM_SESSION_MISMATCH`,
`LOADING_CHECKLIST_INCOMPLETE`, `LOADING_STATUS_TRANSITION_NOT_ALLOWED` e
`TRUCK_OPERATION_CONFLICT`.

`CONFIRMADO` (OC64): `POST /loading-sessions` retorna `409
TRUCK_OPERATION_CONFLICT` quando o caminhão do plano já estiver reservado por
outra operação ativa. `details` identifica `truck_id`. A validação ocorre no
backend e é protegida pelo bloqueio transacional do caminhão.

### Conferência por código — OC76

`CONFIRMADO`: `POST /loading-sessions/{session_id}/scan` recebe
`{"code":"loadx:loading-item:<UUID canônico minúsculo do item do checklist>"}`.
O prefixo é literal, sem espaços; o código possui 55 caracteres. `items[].code`
nas respostas de criação, leitura e atualização fornece o mesmo identificador
para OC75, sem consulta direta ao banco. A identidade é `loading_session_items.id`,
não código do produto nem índice de volume. Não há etiqueta física ou imagem.

`CONFIRMADO` (v1.2.0): `ADMIN` ou `CHECKER` pode conferir por código, com sessão autenticada,
origem permitida e token CSRF, como na OC66. Código não é credencial. O endpoint
retorna `200 LoadingSessionRead`, com apenas o item identificado em `CHECKED`.
Sessão deve estar `IN_PROGRESS`; o bloqueio transacional de sessão/item é o mesmo
da conferência manual. Finalização continua exigindo todos os itens conferidos.

| Situação | HTTP / código |
|---|---|
| Formato inválido ou campo extra | `422 VALIDATION_ERROR` |
| Sessão inexistente | `404 LOADING_SESSION_NOT_FOUND` |
| Item inexistente | `404 LOADING_ITEM_NOT_FOUND` |
| Item pertence a outra sessão | `409 LOADING_ITEM_SESSION_MISMATCH` |
| Item já conferido, inclusive por operação manual | `409 LOADING_ITEM_ALREADY_CHECKED` |
| Sessão `PENDING` ou `FINISHED` | `409 LOADING_STATUS_TRANSITION_NOT_ALLOWED` |
| Sem autenticação / perfil negado | `401 AUTH_INVALID_TOKEN` / `403 AUTH_FORBIDDEN` |

`CONFIRMADO`: erros não alteram o checklist. Leitura repetida não confirma outro
volume; a conferência manual mantém sua idempotência anterior. Duas leituras do
mesmo item são serializadas pelo bloqueio da sessão: uma confirma e a outra
recebe conflito. UUIDs de sessão/item são imutáveis; não há migration.

## Viagens e entregas

`CONFIRMADO` (OC65): `POST /trips` e a transição efetiva para `IN_ROUTE` em
`PATCH /trips/{id}/status` retornam HTTP `409` com código estável
`DRIVER_OPERATION_CONFLICT` quando outra viagem `SCHEDULED` ou `IN_ROUTE`
reserva o motorista. `details` contém
`[{"field": "driver_id", "value": "uuid-do-motorista"}]`.
Nenhuma alteração parcial de viagem, entregas, pedidos ou histórico é salva.


- `GET /trips`.
- `POST /trips`.
- `GET /trips/{id}`.
- `PATCH /trips/{id}/status`.
- `PATCH /deliveries/{id}/status`.

### GET `/trips`

`CONFIRMADO`: a listagem usa `page` 1-based, `page_size` entre 1 e 100 e
`sort_order` `asc` ou `desc`, com os defaults gerais deste contrato. A resposta
usa o envelope `items`, `page`, `page_size`, `total` e `total_pages` e ordena
por `created_at` e `id` na mesma direção.

Cada item contém somente `id`, `load_plan_id`, `driver_id`, `status`,
`started_at`, `finished_at`, `created_at` e `delivery_count`. Nome, telefone,
documento, CNH, cliente, endereço e e-mail não fazem parte da listagem.

`ADMIN` e `LOGISTICS_MANAGER` listam todas as viagens. `DRIVER` lista somente
viagens vinculadas ao próprio `users.driver_id`; ausência de vínculo ou
motorista inexistente/inativo retorna `403 AUTH_FORBIDDEN`. `CHECKER` não
acessa a rota. Não existe filtro público por `driver_id`.

Exemplo de criação por `LOGISTICS_MANAGER`:

```json
{
  "load_plan_id": "uuid-do-plano-aprovado",
  "driver_id": "uuid-do-motorista-ativo"
}
```

Resposta `201`:

```json
{
  "id": "uuid-da-viagem",
  "load_plan_id": "uuid-do-plano-aprovado",
  "driver_id": "uuid-do-motorista-ativo",
  "status": "SCHEDULED",
  "started_at": null,
  "finished_at": null,
  "deliveries": [
    {
      "id": "uuid-da-entrega",
      "trip_id": "uuid-da-viagem",
      "order_id": "uuid-do-pedido",
      "status": "PENDING",
      "sequence": 1,
      "delivered_at": null
    }
  ]
}
```

Corpo das transições:

```json
{
  "status": "IN_ROUTE"
}
```

`CONFIRMADO`: `PATCH /trips/{id}/status` retorna `TripRead`, com as entregas da
viagem. `PATCH /deliveries/{id}/status` retorna somente a entrega alterada em
`DeliveryRead` (`id`, `trip_id`, `order_id`, `status`, `sequence`, `delivered_at`),
conforme `deliveries/router.py`; não retorna a viagem inteira. Esta descrição
explicita o contrato implementado, sem alterar a API.

Regras de autorização:

- `ADMIN` e `LOGISTICS_MANAGER` criam viagem;
- `ADMIN` e `LOGISTICS_MANAGER` consultam qualquer viagem;
- `ADMIN` e `LOGISTICS_MANAGER` alteram viagem ou entrega conforme estados válidos;
- `DRIVER` consulta e altera somente viagem atribuída ao seu `driver_id`, desde
  que usuário e motorista continuem ativos;
- `ADMIN` não personifica motorista nem ignora o vínculo exigido para `DRIVER`; `CHECKER` não acessa essas rotas.

Regras do contrato:

- criação exige plano operacional `APPROVED`, motorista elegível e pedidos
  `PLANNED`; partes de distribuição OC90 também aceitam `IN_TRANSIT`. Legado
  exige pedido sem entrega; multi permite outra parte válida da mesma distribuição;
- uma entrega é criada por pedido do plano/parte, com `sequence` contígua 1-based;
- viagem aceita `SCHEDULED -> IN_ROUTE -> FINISHED`;
- entrega aceita `PENDING -> IN_DELIVERY -> DELIVERED` somente durante
  `IN_ROUTE`;
- repetir o status atual é idempotente e não cria novo histórico;
- início exige carregamento finalizado do mesmo plano e move somente pedidos
  `PLANNED` para `IN_TRANSIT`, sem repetir transição de outra parte;
- conclusão de entrega move o pedido para `DELIVERED` quando todas as suas
  pernas necessárias concluíram (legado tem uma). Viagem multi exige somente
  suas próprias entregas `DELIVERED`; legado exige também seus pedidos;
- timestamps de início, entrega e fim são retornados em UTC.

Erros específicos:

- `TRIP_NOT_FOUND` e `DELIVERY_NOT_FOUND`;
- `TRIP_LOAD_PLAN_NOT_FOUND`, `TRIP_LOAD_PLAN_NOT_APPROVED` e
  `TRIP_LOAD_PLAN_ALREADY_ASSIGNED`;
- `TRIP_DRIVER_NOT_FOUND` e `TRIP_DRIVER_INACTIVE`;
- `TRIP_ORDER_ALREADY_ASSIGNED`, `TRIP_ORDER_NOT_ELIGIBLE` e
  `TRIP_DELIVERY_SEQUENCE_CONFLICT`;
- `TRIP_LOADING_NOT_FINISHED` e `TRIP_DELIVERIES_NOT_FINISHED`;
- `DELIVERY_TRIP_NOT_IN_ROUTE`;
- `TRIP_STATUS_TRANSITION_NOT_ALLOWED` e
  `DELIVERY_STATUS_TRANSITION_NOT_ALLOWED`;
- `TRUCK_OPERATION_CONFLICT`: conflito `409` quando o caminhão do plano já
  pertence a outra operação ativa.

`CONFIRMADO` (OC64): `POST /trips` reutiliza a mesma regra de conflito aplicada
ao carregamento. O erro retorna `truck_id` em `details`. Nenhum endpoint mantém
uma implementação própria da regra.

### Comprovante operacional — OC78

`CONFIRMADO` pela ADR-024 e pela revisão do PR #98: contrato aditivo do
comprovante operacional conforme a
[ADR-024 aceita](decisions/ADR-024-comprovante-operacional-entrega.md).
Os contratos anteriores de `TripRead`, `DeliveryRead` e status permanecem iguais.

- `POST /deliveries/{id}/receipt`: registra a conclusão pelo ciclo existente e
  retorna o comprovante. Corpo obrigatório `{}`, sem campos adicionais.
- `GET /deliveries/{id}/receipt`: consulta o comprovante da entrega concluída,
  inclusive pelo fluxo de status anterior. Não registra nova conclusão.

Ambas retornam `200` com `DeliveryReceiptRead`:

```json
{
  "id": "uuid-do-historico-da-conclusao",
  "delivery_id": "uuid-da-entrega",
  "trip_id": "uuid-da-viagem",
  "order_id": "uuid-do-pedido",
  "driver_id": "uuid-do-motorista-da-viagem",
  "delivered_at": "2026-09-30T20:00:00Z",
  "recorded_at": "2026-09-30T20:00:00Z",
  "recorded_by": "uuid-do-usuario-que-concluiu"
}
```

O servidor obtém todos os campos de registros persistidos; o cliente não pode
informar entrega/viagem/pedido alternativos, responsável, horário, recebedor,
foto, assinatura ou localização. `id` identifica o histórico, não um arquivo.
`recorded_at` e `delivered_at` são horários distintos, normalizados para UTC.
Não há referência de evidências, sequer URL mock ou alegação de upload.

`POST` exige `ADMIN`, `LOGISTICS_MANAGER` ou `DRIVER` vinculado/ativo na própria viagem;
`GET` admite os três perfis. `CHECKER` é negado. Sessão em cookie é obrigatória;
`POST` exige Origin aprovada e CSRF. Autorização por objeto ocorre antes de
verificar estado/histórico. A primeira conclusão exige `IN_DELIVERY` e viagem
`IN_ROUTE`, conclui a própria perna e move o pedido para `DELIVERED` somente
quando todas as partes necessárias concluíram; compartilha commit com os históricos. Repetição autorizada retorna o mesmo `id`, horários e responsável,
sem novo histórico, inclusive após `FINISHED`.

| Status | Código | Condição |
| --- | --- | --- |
| `401` | `AUTH_INVALID_TOKEN` | Sessão ausente/inválida. |
| `403` | `AUTH_FORBIDDEN` | Perfil ou viagem sem autorização. |
| `403` | `AUTH_ORIGIN_FORBIDDEN` / `AUTH_CSRF_INVALID` | Proteções atuais de escrita. |
| `404` | `DELIVERY_NOT_FOUND` / `TRIP_NOT_FOUND` | Vínculo operacional inexistente. |
| `409` | `DELIVERY_STATUS_TRANSITION_NOT_ALLOWED` | Registro exige transição atual permitida. |
| `409` | `DELIVERY_TRIP_NOT_IN_ROUTE` | Primeira conclusão fora de viagem em rota. |
| `409` | `TRIP_ORDER_NOT_ELIGIBLE` | Pedido fora de `IN_TRANSIT` na conclusão. |
| `409` | `DELIVERY_RECEIPT_NOT_AVAILABLE` | Consulta de entrega ainda não concluída. |
| `409` | `DELIVERY_RECEIPT_HISTORY_INVALID` | Conclusão sem histórico único e responsável. |
| `422` | `VALIDATION_ERROR` | UUID inválido, corpo ausente ou campos adicionais. |

`PENDENTE DE DEFINIÇÃO`: evidências reais, recebedor, correções e retenção exigem
novo contrato aprovado; a base não cria campos reservados que indiquem recursos
inexistentes. Não se adiciona requisito de comprovante para finalizar a viagem.

## Histórico de status

`CONFIRMADO`: criação e mudanças efetivas de pedidos, planos, viagens e entregas
gravam `ORDER`, `LOAD_PLAN`, `TRIP` ou `DELIVERY` em `status_history`, na mesma
transação do agregado.

`CONFIRMADO` por D10: a OC09 não expõe endpoint público para consulta de
histórico.

## Ocorrências

- `POST /occurrences`.
- `GET /trips/{id}/occurrences`.

Exemplo de criação:

```json
{
  "trip_id": "uuid",
  "delivery_id": "uuid",
  "type": "DAMAGED_PRODUCT",
  "description": "Uma caixa foi danificada durante a entrega.",
  "photo_url": "mock://occurrences/photo-1"
}
```

`CONFIRMADO`: `photo_url` permanece opcional. Quando informado, aceita somente
`mock://occurrences/<identificador>`, com identificador alfanumérico que também
pode conter `.`, `_` ou `-`. Referências vazias, HTTP/HTTPS, espaços, query
string e fragmento retornam `422 VALIDATION_ERROR`.

`CONFIRMADO`: a API armazena apenas a referência textual. Não existe endpoint
de upload, armazenamento binário, bucket ou consulta externa de mídia no MVP.

## Mensagens e WhatsApp

`CONFIRMADO` (decisão de manutenção vinculada à OC82): envio e simulador permanecem exclusivamente mock, conforme
[ADR-036](decisions/ADR-036-whatsapp-mock.md) e
[contrato interno](../backend/app/integrations/whatsapp/README.md). O contrato
público permanece o existente. `PENDENTE DE DEFINIÇÃO`: integração real adiada;
fornecedor, credenciais, retries e idempotência durável de saída serão tratados
quando esse escopo for retomado. Recepção/webhook pertence à OC83.


- `POST /messages/interpret`: simulador interno disponível somente para usuários
  autenticados com papel `ADMIN` ou `LOGISTICS_MANAGER`.
- `POST /webhooks/whatsapp` permanece fora da v1.0.0; o provider controlado usa
  `POST /messages/interpret`.

`CONFIRMADO`: `driver_phone` identifica o motorista que o operador interno
pretende simular; esse campo não autentica nem autoriza a requisição. O endpoint
não representa autenticação real do WhatsApp. Provider real, webhook e validação
de assinatura permanecem fora deste MVP.

Exemplo de interpretação:

```json
{
  "driver_phone": "+5500000000000",
  "message": "Ja cheguei no cliente"
}
```

Resposta recomendada:

```json
{
  "intent": "ARRIVED",
  "confidence": 0.91,
  "allowed": true,
  "action": "UPDATE_DELIVERY_STATUS"
}
```

`CONFIRMADO`: a resposta inclui `executed`, `confirmation`, `trip_id` e
`delivery_id`. A intenção só vira ação após identificar motorista/viagem/entrega
e o `TripService` validar permissão e estado. Nenhuma regra de viagem ou entrega
é duplicada no módulo de mensagens.

### Notificações automáticas — OC84

`CONFIRMADO`: não há endpoint público novo. Permissões, autorização por viagem,
401/403, Origin e CSRF continuam nos endpoints existentes. GET não cria notificações.
Os eventos reais de início de viagem e ocorrência geram registros duráveis,
idempotentes por tipo/origem/motorista; saída WhatsApp é exclusivamente mock.

`CONFIRMADO`: o registro é atômico com o fato. Claim persistente posterior ao commit
externo autoriza no máximo uma tentativa local; falha do mock não desfaz domínio.
OC79/OC83 respeitam savepoints e replay. SIMULATED não equivale a envio ou entrega
externa. O simulador preserva sua confirmação sem segundo aviso automático.
Consulta interna do service não altera estado nem inicia tentativas.

`CONFIRMADO`: schema/estados em docs/03 e ADR-041. OC103 definirá central/leitura,
preferências e acesso por destinatário; OC109 definirá recuperação de pendências,
worker/retries. Nenhuma dessas APIs foi antecipada nesta OC84.


## Auditoria — OC97

### GET `/audit`

Consulta somente leitura permitida a `ADMIN` e `LOGISTICS_MANAGER`.
`CHECKER` e `DRIVER` recebem `403 AUTH_FORBIDDEN`.

A resposta usa o envelope paginado padrão e agrega:

- mudanças de `status_history` como `event_type = STATUS_CHANGED`;
- ações administrativas selecionadas de `audit_events`, inicialmente
  `USER_CREATED` e `USER_UPDATED`.

Filtros opcionais, sempre aplicados no servidor antes da paginação:

- `entity_type`: `ORDER`, `LOAD_PLAN`, `TRIP`, `DELIVERY` ou `USER`;
- `entity_id`: UUID do registro;
- `actor_id`: UUID do usuário responsável;
- `event_type`: `STATUS_CHANGED`, `USER_CREATED` ou `USER_UPDATED`;
- `start_at` e `end_at`: período com timezone;
- `page`, `page_size` e `sort_order`: paginação padrão.

Cada item retorna `actor_id` e `actor_name` quando houver usuário responsável,
`old_status/new_status` para mudança operacional e `changed_fields` para ação
administrativa.

`CONFIRMADO`: `changed_fields` contém somente nomes de campos. Valores de nome,
e-mail, senha, token, sessão ou payload sensível não são persistidos nem retornados.

`CONFIRMADO`: não existem endpoints POST, PUT, PATCH ou DELETE de auditoria.

## Relatórios

- `GET /reports/load-plans/{id}`.
- `GET /reports/trips/{id}`.

`CONFIRMADO`: ambos retornam `application/pdf` com `Content-Disposition:
attachment`. O relatório é gerado em memória a partir dos dados persistidos e
não exige armazenamento permanente na v1.0.0.

`CONFIRMADO`: as duas rotas PDF aceitam somente `ADMIN` e `LOGISTICS_MANAGER`,
conforme `ReportUser` em `reports/router.py`.

## Erros

Formato padrão:

```json
{
  "code": "LOAD_PLAN_INVALID",
  "message": "O plano possui volumes fora dos limites.",
  "details": []
}
```

Regras:

- `code`: string estável em UPPER_SNAKE_CASE.
- `message`: texto claro para interface ou log operacional.
- `details`: lista com campos, IDs ou motivos de validação.
- `VALIDATION_ERROR`: payload, path ou query não atende ao schema; usa status `422` e identifica os campos inválidos em `details`.
- `INTERNAL_SERVER_ERROR`: falha inesperada; usa status `500`, mensagem pública genérica e `details` vazio, sem expor informações internas.
- `CONFIRMADO`: o OpenAPI referencia o mesmo schema `ErrorResponse` para os erros públicos documentados em cada operação.

Mapeamento recomendado:

- `400`: entrada inválida ou regra de negócio violada.
- `401`: autenticação ausente ou inválida.
- `403`: perfil sem permissão.
- `404`: entidade não encontrada.
- `409`: conflito de estado, duplicidade ou versão.
- `422`: validação de schema.
- `500`: erro inesperado.

## Segurança de API

- Somente `GET /health`, `GET /ready` e `POST /api/v1/auth/login` são públicos.
- Endpoints de negócio da interface exigem cookie de sessão e a matriz de
  `docs/04-regras-negocio.md`. O POST exato `/api/v1/webhooks/controlled-events`
  exige assinatura HMAC e autorização OC79, sem cookie; não é público/anônimo.
- Nas rotas de sessão, `POST`, `PUT`, `PATCH` e `DELETE` exigem `Origin` na lista
  exata de CORS e operações autenticadas exigem `X-CSRF-Token`. Apenas o POST
  assinado da OC83 usa autenticação de emissor em lugar dessas proteções de navegador.
- `CONFIRMADO`: com `APP_ENV=local`, `/docs`, `/docs/oauth2-redirect`, `/redoc` e `/openapi.json` ficam disponíveis. Com `APP_ENV=production` ou sem a variável, essas rotas não são registradas e retornam `404`.
- Senhas nunca retornam na API.
- Tokens e segredos nunca aparecem em logs.
- Dados pessoais devem ser minimizados em respostas de listagem.
- Endpoints que alteram status devem registrar histórico.
- Integrações externas devem ser autenticadas quando saírem do modo mock.

`CONFIRMADO`: CORS permite credenciais somente para as origens exatas de
`BACKEND_CORS_ORIGINS` e expõe `X-CSRF-Token` ao frontend próprio.

`CONFIRMADO`: todas as respostas da aplicação usam `Cache-Control: no-store`,
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`, política restritiva de permissões e CSP que
impede framing. Em `production`, também usam `Strict-Transport-Security` por um
ano com `includeSubDomains`.

`CONFIRMADO`: novos hashes de senha usam Argon2id com memória de 19 MiB, duas
iterações e paralelismo 1. PBKDF2 legado é aceito apenas para migração gradual
após autenticação válida.

`CONFIRMADO`: a autorização por perfil segue `ADR-004`; acesso não listado é negado.

`CONFIRMADO`: a OC79 implementa uma fronteira interna de autenticidade,
autorização e idempotência, sem adicionar endpoint HTTP ou mudar o simulador.
Contrato, catálogo fechado, erros e consumo pelas OCs seguintes estão em
[external_commands/README](../backend/app/modules/external_commands/README.md)
e na proposta [ADR-026](decisions/ADR-026-seguranca-comandos-externos.md).

`CONFIRMADO`: OC83 compõe HMAC, bindings confiáveis e recebimento HTTP controlado
em [messages/inbound](../backend/app/modules/messages/inbound.md). OC82 mantém
WhatsApp mock. `PENDENTE DE DEFINIÇÃO`: autenticação/formato Meta específico
permanece na pré-produção (#193); sessão/Origin/CSRF e RBAC da interface são preservados.

## OC105 — cadastros ativos e arquivados

`CONFIRMADO`: GET de `/customers`, `/products`, `/trucks` e `/drivers` aceita
`archive_status=active|archived|all` (default `active`). O filtro é whitelist,
não recebe dados pessoais, e precede COUNT/LIMIT/OFFSET. Detalhe por UUID mantém
arquivados acessíveis aos mesmos leitores. Clientes/produtos passam a retornar
`active` booleano; os demais campos e o envelope paginado são preservados.

`CONFIRMADO`: PATCH `/{id}` com `{"active": false}` arquiva e com `true` reativa,
retornando 200 no schema existente. `ADMIN` ou `LOGISTICS_MANAGER` escreve; sessão,
origem e CSRF permanecem obrigatórios. `null` é inválido (422), ID ausente 404,
unicidade global 409. Repetir o mesmo estado não duplica auditoria. Operação nova
com fonte arquivada retorna 409 `RECORD_ARCHIVED`, com entidade e UUID em
`details`, sem dados pessoais. Conflitos operacionais anteriores mantêm seus
códigos. Consulta de situação da frota mantém a visão completa da OC67/68/72;
as seleções operacionais usam somente registros ativos/disponíveis.

## OC99 — endereços de cliente e destino contratado

`CONFIRMADO`: ADMIN e LOGISTICS_MANAGER acessam GET/POST
`/api/v1/customers/{customer_id}/addresses` e PATCH
`/api/v1/customers/{customer_id}/addresses/{address_id}`. Coleção usa paginação
padrão e archive_status=active|archived|all; default active. CREATE exige
address/city/state, aceita label (default Principal), postal_code opcional
(8 dígitos ou máscara), active e is_primary. PATCH aceita campos parciais;
postal_code pode ser null, outros campos enviados não podem ser null.
Arquivamento/reativação usa active, sem DELETE. UUID é estável. Principal
arquivado promove o ativo mais antigo; se nenhum permanecer, projeção legada
mantém último endereço. Erros: 401/403 sessão/RBAC, 404 origem não encontrada,
409 principal inválido, 422 entrada inválida e 500 envelope comum.

`CONFIRMADO`: POST /orders admite exatamente um de customer_address_id ou
delivery_address. Endereço selecionado pertence ao cliente e deve estar ativo;
backend copia snapshot e texto. GET detalhado e respostas de escrita acrescentam
customer_address_id e delivery_address_snapshot. PATCH DRAFT sem destino mantém
a cópia; novo destino explicitamente selecionado/textual substitui a cópia.
Troca de cliente exige destino explícito. Seleção inexistente/de outro cliente
recebe 422, arquivada recebe 409. Consulta pública resumida continua minimizada.

## OC100 — manutenção da frota

`CONFIRMADO`: GET/POST `/api/v1/trucks/{truck_id}/maintenances` lista histórico
paginado/cria manutenção; POST `/{maintenance_id}/close` encerra/cancela período.
ADMIN e LOGISTICS_MANAGER escrevem; CHECKER lê, DRIVER recebe 403. CREATE:
kind PREVENTIVE|CORRECTIVE, starts_at com fuso, ends_at opcional exclusivo,
description, workshop/notes/cost opcionais e odometer_km opcional inteiro.
CLOSE: odometer_km e next_service_at/km opcionais; campos omitidos preservam
revisão, null limpa critério. Repetir encerramento retorna 409. Não há DELETE.
Erros 401/403 sessão/RBAC, 404 origem inexistente, 409 conflito/arquivado/km
reduzido, 422 período/revisão/entrada inválida, 500 envelope comum.

`CONFIRMADO`: TruckRead acrescenta odometer_km e next_service_at/km opcionais;
CREATE/PATCH truck admitem odometer_km (PATCH não admite null). Status da frota
acrescenta has_maintenance_conflict e available considera esse bloqueio.
Novas operações com manutenção atual recebem TRUCK_IN_MAINTENANCE (409);
preflight de distribuição apresenta esse motivo entre os ineligíveis.

## OC101 — documentos dos caminhões

`CONFIRMADO`: GET/POST `/api/v1/trucks/{truck_id}/documents`; POST
`/documents/{document_id}/renew`; GET `/document-policies`; PATCH
`/document-policies/{kind}` (todos sob o mesmo caminhão). GET documents usa o
envelope paginado ADR-017, inclui versões históricas e `status` derivado.
Create/renew recebem kind CRLV|LICENSING|INSURANCE, reference (1–120),
issued_at/expires_at UTC opcionais e file_reference UUID opcional. Read adiciona
id/truck_id/created_at/superseded_at/status. Renovação retorna novo UUID (201).
Policy PATCH exige boolean estrito required; GET retorna políticas configuradas
(não configurada equivale a false). Sem DELETE nem atualização destrutiva.
RBAC do cadastro: ADMIN/LOGISTICS_MANAGER escreve, CHECKER lê, DRIVER negado.
Erros 401/403/404/409/422 padrão. Duplicidade TRUCK_DOCUMENT_DUPLICATE;
renovação obsoleta TRUCK_DOCUMENT_NOT_CURRENT; ausência TRUCK_DOCUMENT_NOT_FOUND.
Política documental violada: TRUCK_DOCUMENT_INELIGIBLE (409).
Operational-status acrescenta has_document_conflict e available incorpora
políticas; preflight usa motivo TRUCK_DOCUMENT_INELIGIBLE. Endpoints anteriores
permanecem compatíveis. Referência de arquivo nunca é URL/caminho ou download.

## OC102 — documentos de motoristas

`CONFIRMADO`: GET/POST `/api/v1/driver-document-types` lista/aprova tipos com
id UUID, code único uppercase (32) e name (120); CNH é nativo.
GET/POST `/api/v1/drivers/{driver_id}/documents`; POST
`/documents/{document_id}/renew` (201, nova identidade); GET `/document-policies`;
PATCH `/document-policies/{document_type_id}`. Todos sob prefixo do motorista.
Documents usa paginação ADR-017, inclui versões históricas e status derivado.
Create recebe document_type_id, reference, category opcional somente CNH,
issued_at/expires_at UTC opcionais; versão CNH explicitamente criada/renovada
exige expires_at. Read acrescenta id/driver_id/created_at/superseded_at/status.
Policy PATCH recebe required boolean estrito e allowed_categories lista única
C/D/E/AC/AD/AE somente para CNH (default [], sem restrição extra).
CRUD de drivers acrescenta license_expires_at opcional; omissão preserva, null
limpa validade e torna inelegível se CNH exigida. Novas categorias usam catálogo
atual; leituras legadas preservam strings antigas. Resumos não expõem CNH/CPF.
Operational-status acrescenta has_document_conflict; available incorpora a
política. DriverService valida designação/início de viagem com erro 409
DRIVER_DOCUMENT_INELIGIBLE. RBAC atual ADMIN/LOGISTICS_MANAGER leitura/escrita;
CHECKER/DRIVER negados. Erros padrão 401/403/404/409/422; sem DELETE, arquivo,
storage ou envio de notificações. Eventos documentais na auditoria para OC103.

## OC110 — anexos operacionais

`CONFIRMADO`: API aditiva `/api/v1/attachments/{resource_type}/{resource_id}`
para orders/trips/deliveries/occurrences; POST registro, GET página, GET /{id}
metadata, GET /{id}/content protegido, POST /{id}/revoke lógico. DTOs
AttachmentCreate/AttachmentRead preservam todos os schemas anteriores. Contrato,
erros e RBAC completos em [README do módulo](../backend/app/modules/attachments/README.md)
e [ADR-033](decisions/ADR-033-anexos-operacionais.md). Sem URL de storage,
client-supplied MIME/autor, novos formatos ou ativação de fornecedor em produção.

## OC104 — importação de cadastros

`CONFIRMADO`: `/api/v1/registration-imports`, ADMIN/LOGISTICS_MANAGER ativos.
Tipos customers/products/trucks/drivers; GET /{entity_type}/template, POST
/{entity_type}/preview, POST /{entity_type}/confirm, GET histórico paginado com
entity_type e GET /{import_id}. Prévia: file_name/content_base64; confirmação
acrescenta preview_sha256/event_id UUID. Prévia expõe linhas normalizadas e
can_confirm; resultado COMPLETED/REJECTED contém totais, autor, data, checksum,
erros por linha/campo e UUIDs criados. Arquivo inválido não cria cadastros.
[Contrato completo](../backend/app/modules/registration_imports/README.md).

## OC91 — cadastro institucional da empresa

`CONFIRMADO`: `GET /api/v1/company-profile` e `PUT /api/v1/company-profile`
são exclusivos de ADMIN ativo, com sessão/CSRF/origem existentes. GET retorna
`null` antes do primeiro cadastro e não escreve dados. PUT substitui o cadastro
único e retorna 200 com `id`, os seis campos e timestamps `created_at/updated_at`.

| Campo | Contrato |
| --- | --- |
| `legal_name`, `display_name` | Obrigatórios, texto não vazio após trim, até 160 caracteres |
| `cnpj` | Opcional, CNPJ numérico válido; retorna 14 dígitos |
| `phone` | Opcional, regra existente de telefone com DDD; retorna dígitos |
| `email` | Opcional, formato existente, até 255 caracteres; retorna minúsculas |
| `logo_reference` | Opcional, URL HTTPS sem credenciais, até 2048 caracteres; apenas metadado |

Vazio opcional equivale a null; campos desconhecidos são recusados. Sem sessão:
401; outros perfis: 403; entrada inválida: 422 no envelope padrão com erros por
campo. Não há DELETE, upload, fetch remoto, tenant, cadastro paralelo de usuários
ou credenciais de integração. Atualizações concorrentes são serializadas no
PostgreSQL: última gravação válida prevalece, sem auditoria de no-op.

Auditoria institucional usa `COMPANY_PROFILE` e eventos
`COMPANY_PROFILE_CREATED/COMPANY_PROFILE_UPDATED`. ADMIN pode filtrá-los na API;
consultas gerais de LOGISTICS_MANAGER os excluem e filtros explícitos recebem
403. Histórico contém somente ator, data e nomes dos campos, sem valores.
Fora desse histórico institucional, as permissões existentes são preservadas.
Detalhes: [ADR-035](decisions/ADR-035-configuracoes-institucionais-standalone.md).

## OC108 — Integrações e Saúde

`CONFIRMADO`: `GET /api/v1/integration-health`, exclusivo ADMIN ativo. Retorna
200 com falhas parciais em indicadores; 401/403/422/500 no envelope existente.
Campos: `checked_at` UTC, `correlation_id` UUID da consulta, `overall_status`
PARTIAL/DEGRADED, `components` com nome do componente, modo INTERNAL/MOCK/REAL,
status fechado, configured boolean/null e reason_code fechado. Sem segredos,
URLs, traces, dados pessoais ou configuração bruta. Consulta passiva sem envios,
prompts ou alterações. Reusa liveness/readiness e timeouts existentes.

WhatsApp SIMULATED (UI SIMULADO), IA mock SIMULATED, IA externa não implementada
NOT_CONFIGURED. Webhook interno: NOT_CONFIGURED quando o runtime está desativado;
AVAILABLE/RUNTIME_CONFIGURED quando inicializado, sem certificar conexão externa.
Notificações internas: LIMITED/WORKER_NOT_OBSERVED, reconhecendo OC84/OC103/OC109
implementadas, sem afirmar que o worker está ativo. Códigos OC83_PENDING e
OC84_PENDING são mantidos no catálogo por compatibilidade, sem emissão padrão.
Sinais futuros aprovados podem informar AVAILABLE,
UNAVAILABLE e TIMEOUT; não são criados providers nesta OC. Consultas paralelas
com falha isolada e configuração desconhecida null. Histórico durável indisponível;
falhas atuais são correlacionadas por UUID/data e logs sanitizados.
Contrato detalhado: [integration_health](../backend/app/modules/integration_health/README.md).


## OC92 — Minha conta standalone

`CONFIRMADO`: `GET /api/v1/auth/me` continua restaurando usuário e CSRF. Novos contratos próprios: `PATCH /auth/me` (nome/e-mail), `POST /auth/me/password` (confirmação atual e senha nova), `GET /auth/me/sessions`, `DELETE /auth/me/sessions/{session_id}` e `POST /auth/me/sessions/revoke-others`, todos sob prefixo `/api/v1`.

`CONFIRMADO`: todos os perfis autenticados acessam apenas a própria conta. Sem role/active/driver_id editáveis, hashes/tokens nas respostas ou ID de usuário arbitrário. UUID de sessão é referência pública de revogação, não credencial. Sessões listadas são próprias, não revogadas, dentro dos dois prazos existentes; `current` vem da sessão autenticada. Falhas retornam envelope sanitizado; 401/403 e Origin/CSRF mantidos. Senha inválida 400, duplicidade de e-mail 409, schema/política 422, throttling 429. Sessão alheia/inexistente 404 indistinguível.

`CONFIRMADO`: senha válida revoga todas as sessões e exige novo login (204 + remoção do cookie), na mesma transação de hash/auditoria. Revogar as outras preserva a atual; revogar a atual encerra autenticação. Contrato completo e concorrência em [auth/README](../backend/app/modules/auth/README.md). Política: ADR-020; sem migration ou novo modo de identidade/CoreFlow.


### Contagem física em listagem de pedidos — manutenção #204

`GET /api/v1/orders` retorna agora `volume_count` (inteiro não negativo) para
cada resumo, além de `item_count`. O primeiro é
`sum(order_item.quantity)`, correspondente aos volumes expandidos avaliados
pelo planejamento; `item_count` continua representando a quantidade de linhas
de produto. Trata-se de campo aditivo, sem expor `items` completos ou endereço
no resumo. O contrato do cálculo `POST /load-plans` permanece inalterado:
máximo de 200 volumes e erro 422 com `volume_count` e `max_volumes` nos
detalhes quando o limite é superado.

### OC98 — recuperação e segundo fator standalone

`CONFIRMADO`: contrato aprovado na ADR-038 e detalhado em [auth/README](../backend/app/modules/auth/README.md#oc98--recuperação-de-senha-e-mfa).
Login mantém UserRead para perfis sem MFA; para ADMIN/LOGISTICS_MANAGER retorna
MfaChallengeRead sem sessão. `POST /auth/mfa/verify` é a única conclusão desse
desafio. Recuperação tem solicitação neutra e confirmação 204 sem autenticação.
Rotas próprias de MFA exigem cookie/CSRF/ownership e reautenticação reforçada.
Nenhuma mudança nos contratos logísticos, planos, snapshots, OC88 ou OC93.

## OC107 — Busca global

`CONFIRMADO`: `GET /api/v1/search` exige sessão e `search` obrigatório (2–120
caracteres após trim). `limit_per_category`: 1–10, default 5. Resposta 200:
`{"results":[{"category":"order","id":"UUID","title":"Pedido UUID","href":"/orders?order=UUID"}]}`.
Categorias `order/customer/truck/driver/trip`; sem totais de sugestões omitidas.
Reuso da semântica literal/case-insensitive da OC95, acentos preservados. Cadastros
ativos; ordenação created_at/id descendente por categoria. Limite, não paginação
global; ver [ADR-039](decisions/ADR-039-busca-global-limitada.md).

ADMIN/LOGISTICS_MANAGER: todos os cinco tipos; CHECKER: somente pedidos (sem
nomes de clientes na pesquisa/título) e caminhões; DRIVER: somente UUID das
próprias viagens, com vínculo ativo validado pelo TripService. Nenhum dado,
contagem ou categoria restrita é retornado. 401 sem sessão, 403 vínculo de DRIVER
inválido/inativo, 422 parâmetros inválidos. URLs de cadastros abrem listagens com
`search` e `tab` apropriados; pedidos/viagens usam detalhes existentes.
Campos e limites completos em [global_search](../backend/app/modules/global_search/README.md).

## OC86 — Gestão administrativa de usuários

`CONFIRMADO`: reutiliza GET/POST /api/v1/users e GET/PATCH /api/v1/users/{id},
sempre ADMIN-only. GET da coleção mantém o envelope paginado e os campos
existentes; acrescenta `email`, `driver_id` e `driver_name` (vínculo/nome nullable), conforme extensão da
ADR-017. Aceita `search` opcional por nome (trim, até 120 caracteres, substring
literal case-insensitive, acentos preservados), `role` do catálogo existente e
`active` booleano. Combinam por AND antes da paginação determinística; parâmetros
inválidos recebem 422. Nenhuma nova rota, migration ou mecanismo de autenticação.

`CONFIRMADO`: escritas mantêm contratos, códigos de erro, último ADMIN ativo,
e-mail/vínculo únicos, política de senha, auditoria e revogação transacional de
sessões. DRIVER pode existir sem vínculo conforme API atual; sem vínculo ativo
não acessa viagens próprias. UI informa esse limite e não cria exigência adicional.


## OC112 — Perfis e permissões efetivas

`CONFIRMADO`: /access-profiles adiciona GET/POST da coleção, GET /permissions e
GET/PATCH /{id}, exclusivamente ADMIN. Contrato completo, limites, matriz de
permissões, erros e estratégia transacional em
[access_profiles](../backend/app/modules/access_profiles/README.md).

UserCreate/UserUpdate aceitam role=CUSTOM + custom_profile_id; papéis fixos
preservados e perfil nulo obrigatório. UserRead/login/me acrescentam permissions
e rótulo/UUID do perfil; coleção de usuários acrescenta somente rótulo/UUID do
perfil. Não há endpoints de exclusão ou permissões declaradas pelo cliente usadas
para autorizar. Cookies/CSRF e regras de vínculo permanecem vigentes.

Auditoria ADMIN admite filtros ACCESS_PROFILE e PROFILE_CREATED/PROFILE_UPDATED.
Esses eventos permanecem ocultos ao gerente antes de paginação; escopo legado de
usuários do gerente não é ampliado. ADR-040 substitui o RBAC exclusivamente fixo
onde a ação foi migrada. OC98/tenant/CoreFlow não são incorporados.

## Webhook controlado — OC83

`CONFIRMADO`: `POST /api/v1/webhooks/controlled-events`, assinatura HMAC dos bytes
originais no header `X-LoadX-Signature`, sem sessão/cookie. Reutiliza envelope v1,
capabilities, bindings e idempotência PostgreSQL da OC79. Contrato HTTP, erros,
limites, configuração opt-in e mídia desabilitada em
[messages/inbound](../backend/app/modules/messages/inbound.md).
Somente este POST exato usa assinatura em lugar de Origin/CSRF; demais rotas
preservam as proteções da interface. WhatsApp continua exclusivamente mock.

### OC89 — vínculos de recuperação e caminhão histórico

`CONFIRMADO`: respostas de `GET /load-plans` e `GET /load-plans/{id}` incluem
`distribution_id: UUID | null`, inclusive para versões reprocessadas. Resumos
continuam paginados, sem itens; filtro/ordenação/RBAC não mudam.
`DistributionPartRead` inclui `truck: TruckSnapshotRead` do plano persistido
(placa, modelo, dimensões em cm e capacidade em kg). Não consulta cadastro atual
para reconstruir o histórico. Estes campos aditivos não exigem migration.

## OC103 — notificações pessoais (sessão obrigatória)

`CONFIRMADO`: prefixo `/api/v1/notifications`, sem parâmetro de destinatário.
Todos os perfis autenticados acessam a própria caixa; eventos exigem permissão
real e vínculo atual. ADMIN não consulta caixa alheia. CSRF/Origin nas mutações.

| Método | Caminho | Contrato |
|---|---|---|
| GET | /notifications | PageResponse + unread_count global no mesmo snapshot; page/page_size/sort_order, event_type, category e read opcionais |
| GET | /notifications/unread-count | unread_count visível da sessão |
| POST | /notifications/read-all | updated; leitura idempotente das notificações visíveis |
| POST | /notifications/{id}/read | read_at da primeira leitura; 404 fora da caixa/escopo |
| GET | /notifications/{id}/source | href relativo da viagem, após autorização atual da origem; 404 fora do escopo |
| GET | /notifications/preferences | items: category, enabled, mandatory |
| PUT | /notifications/preferences | items (1–3 categorias únicas); SECURITY false é 422; extras recusados |

Projeção: id, event_type, category, title, summary, created_at (fato), received_at,
read_at. Sem dados do canal/telefone/conteúdo original. Preferência não remove
notificações anteriores nem cria associações retroativas. Erros: 401 sessão,
403 CSRF/Origin, 404 NOTIFICATION_NOT_FOUND, 422 contrato. GETs não gravam nem
simulam envio. Categorias aprovadas: TRIPS/OCCURRENCES; SECURITY é política
obrigatória, sem eventos artificiais. Eventos/alertas futuros exigem contrato próprio.

## OC109 — administração da fila

`CONFIRMADO`: ADMIN autenticado; CSRF/Origin nos comandos. GET /api/v1/outbox-events
com paginação padrão, sort_order, status/event_type; GET /outbox-events/summary;
GET /outbox-events/{id} inclui tentativas; GET /outbox-events/{id}/source revalida
viagem e retorna href; POST /outbox-events/{id}/retry recebe {command_id: UUID},
retorna estado atual. Replay não reinicia fila; reutilização em outra origem 409.
401/403, 404 fora da origem, 409 evento inelegível, 422 contrato. Sem payloads
privados, sem publicação HTTP arbitrária.

`CONFIRMADO` (OC109): /audit admite filtros OUTBOX_EVENT/OUTBOX_REPROCESSED;
somente ADMIN pode consultá-los. Consultas gerais de outros perfis também
excluem essas intervenções administrativas.


## OC90 — operação por parte física

`CONFIRMADO`: endpoints existentes de loading-sessions, trips, deliveries,
receipts e reports operam partes APPROVED de distribuições APPROVED usando
somente seu load_plan atual. Nenhum endpoint novo ou parâmetro de escrita para
atribuir parte. TripCreate mantém load_plan_id/driver_id; o servidor resolve a
parte. Versões históricas e partes não aprovadas continuam recusadas.

`CONFIRMADO`: DeliveryRead acrescenta `distribution_part_id: UUID | null` (null
para legado). O campo é somente de saída. Uma entrega por parte/pedido, com
comprovante independente e contrato DeliveryReceiptRead inalterado. Início da
primeira perna muda Order para IN_TRANSIT; somente conclusão de todas as partes
que transportam esse pedido permite DELIVERED. Trip multi finaliza pelas suas
próprias entregas. Repetições preservam o histórico; POST Trip duplicado continua
409 TRIP_LOAD_PLAN_ALREADY_ASSIGNED. Demais erros/permissões OC112 e regras de
vínculo de motorista permanecem vigentes.

`CONFIRMADO`: GET /reports/load-plans/{id} e GET /reports/trips/{id} continuam PDF
somente leitura. Para distribuição, incluem distribution_id/part_id, plano,
caminhão e quantidade/identidades `(order_item_id, volume_index)` da parte.
Relatório de viagem inclui também trip_id. Não mistura volumes nem recalcula.
GET /audit admite também filtros entity_type=LOAD_DISTRIBUTION e
LOAD_DISTRIBUTION_PART com a mesma permissão reservada de leitura da auditoria.
Nenhum dado pessoal adicional foi incorporado aos schemas ou logs.


## OC81 — comunicação operacional vinculada à entrega

`CONFIRMADO`: `GET /api/v1/deliveries/{delivery_id}/communications`, somente leitura,
aceita `page` >=1, `page_size` 1–100 (padrão20), `sort_order` asc/desc (padrãodesc).
Retorna PageResponse com items, page, page_size, total e total_pages. Cada item:
`id`, `occurrence_id`, `event_type=OCCURRENCE_REGISTERED`, `created_at` UTC,
`channel=WHATSAPP_MOCK`, `simulation_status` e `processing_status` opcional.

Simulation_status conserva o fato OC84: NOT_ATTEMPTED, ATTEMPT_CLAIMED,
SIMULATED, FAILED ou NO_RECIPIENT. Processing_status conserva a projeção OC109:
PENDING, PROCESSING, SUCCEEDED, RETRYABLE, TERMINAL, UNCERTAIN; null significa
que não há fila persistida vinculada. São estados de canal **simulado**, nunca
comprovantes de envio, entrega ou leitura Meta. Não inclui erro interno,
mensagem, telefone, payload, caminho, credencial, ator ou destinatário pessoal.

A origem é a ocorrência cujo delivery_id/trip_id corresponde exatamente à
entrega autorizada; TRIP_STARTED e ocorrências gerais não são atribuídos à
entrega. Ordenação por created_at e UUID na mesma direção. Uma mesma Order em
outra parte/caminhão não amplia o recorte.

Exige sessão ativa e permissões efetivas deliveries.read + occurrences.read,
ou trips.own com DRIVER ativo e vinculado. ADMIN conserva acesso administrativo;
CHECKER e motorista de outra viagem são negados. Erros 401/403/404/422 usam o
envelope padrão (404 DELIVERY_NOT_FOUND). Não há mudança de estados, escrita,
leitura da caixa pessoal, envio, retry, acesso a storage ou migration nessa API.
A UI da OC81 usa exclusivamente este contrato para a seção de comunicação.


## Recuperação idempotente — #254

`CONFIRMADO`: contrato implementado para revisão na ADR-047. Tabela aditiva
`optimization_requests`: PK (user_id, request_key), payload_hash SHA-256 de
versão/seleção ordenada, distribution_id único com FK RESTRICT, created_at UTC.
Persistência atômica com distribuição/planos/volumes/histórico; sem pending ou TTL.
`POST /load-distributions/optimize` aceita header UUID `Idempotency-Key` opcional.
Replay igual retorna 201 com o mesmo recurso atual; payload diferente: 409
IDEMPOTENCY_PAYLOAD_MISMATCH. Concorrência: 409 OPTIMIZATION_IN_PROGRESS.
`GET /load-distributions/optimization-requests/{key}` retorna 200/404/409,
somente para o ator e com a mesma permissão create. Não cria nada.
Migration 20261023_0035 → 20261021_0034; downgrade recusa registros existentes.
Sem alteração de regras físicas, RBAC efetivo, MFA ou OC90/OC94.

## Assistente LoadX consultivo — #336

`CONFIRMADO`: POST `/api/v1/assistant/messages`, sessão/Origin/CSRF, perfis
ADMIN/LOGISTICS_MANAGER/CHECKER. Schema e limites no [README do módulo](../backend/app/modules/assistant/README.md)
e ADR-048. Mensagem até 2.000 caracteres, histórico limitado a oito mensagens;
contexto opcional por plano/distribuição é reconsultado e autorizado no servidor.
Resposta distingue GROQ de FALLBACK e inclui fatos, período, critérios e links
internos autorizados. Sem mutações, cálculos físicos ou autorização pela IA.
Contagens de pedidos completos, pernas e expedição possuem definições separadas.
API legada de explicação permanece; runtime mock usa fallback em vez de declarar
simulação como resposta de IA real. Nenhuma migration ou mudança de estado.

### Assistente: indicadores verificados e falhas de otimização

- Resposta HTTP do chat continua com `answer`, `facts`, `source`, `suggestions`,
  `links`. O texto final do provider é um seletor JSON de orientações, validado
  internamente; não é repassado como prosa ou indicador operacional ao cliente.
- `POST /load-distributions/optimize`, em capacidade insuficiente, preserva código,
  status e detalhes existentes e acrescenta `details[].assistant_diagnostic`.
- `POST /assistant/messages` aceita `diagnostic_token` opcional (até 4.096 caracteres).
  Assinatura, validade de 15 minutos, usuário e permissão são verificados no servidor.
  O diagnóstico é da tentativa anterior, não um novo cálculo nem situação atual.
  `422 ASSISTANT_DIAGNOSTIC_INVALID` para comprovante inválido/expirado/de outro usuário;
  `403` para ausência de permissão. Nunca tratar texto do navegador como diagnóstico.

### Loxi: prioridade de assunto e origem da resposta (#371)

`POST /assistant/messages` mantém autenticação/CSRF e o contrato existente. O campo
`source` também aceita `DOCUMENTATION` (fontes funcionais reais) e `GENERAL`
(conversa geral da IA, sem consulta a registros). A UI identifica essas origens.
Referências opcionais de planejamento não são consultadas numa pergunta explícita
sobre outro módulo. Comparações consultam até dois planos autorizados e nunca
retornam parcialmente um plano proibido; ambiguidades solicitam esclarecimento.
Ferramentas internas incluem catálogo de uso por módulo e leitores paginados de
clientes/motoristas ativos e pedidos. Nenhum endpoint de escrita foi introduzido.
