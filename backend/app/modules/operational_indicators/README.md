# Operational Indicators

Módulo de leitura consolidada dos indicadores operacionais da OC69.

## Endpoint

`GET /api/v1/operational-indicators`

Perfis autorizados:

- `ADMIN`;
- `LOGISTICS_MANAGER`.

`CHECKER` e `DRIVER` não possuem acesso ao dashboard operacional global.

## Catálogo v1.1.0

### Frota

Período: `CURRENT_SNAPSHOT`.

Campos:

- `total`: total de caminhões cadastrados;
- `active`: caminhões com cadastro ativo;
- `inactive`: caminhões com cadastro inativo;
- `available`: caminhões disponíveis segundo OC67/OC68;
- `unavailable`: caminhões não disponíveis no snapshot atual;
- `with_operation_conflict`: caminhões com conflito operacional segundo OC64/OC67.

A disponibilidade não é recalculada neste módulo. A OC69 consome
`TruckOperationalStatusService`, que por sua vez consome
`FleetAvailabilityService`.

### Viagens

Período: `ALL_TIME`.

Campos:

- `total`;
- `scheduled`;
- `in_route`;
- `finished`.

Os valores correspondem diretamente aos estados persistidos
`SCHEDULED`, `IN_ROUTE` e `FINISHED`.

### Entregas

Período: `ALL_TIME`.

Campos:

- `total`;
- `pending`;
- `in_delivery`;
- `delivered`.

Os valores correspondem diretamente aos estados persistidos
`PENDING`, `IN_DELIVERY` e `DELIVERED`.

### Ocorrências

Período: `ALL_TIME`.

Campo:

- `total`: quantidade total de ocorrências registradas.

## Base vazia

Ausência de dados retorna todos os contadores como `0`. O endpoint continua
respondendo `200`.

## Limitações da v1.1.0

A versão não expõe:

- métricas financeiras;
- distância, combustível ou pedágio;
- médias de ocupação;
- séries históricas;
- filtros temporais;
- taxas ou percentuais derivados;
- estimativas de atraso.

Essas métricas não possuem contrato de dados suficientemente uniforme nesta
versão e não são inventadas para preencher o dashboard.

Nenhum indicador é persistido. Todos são calculados em tempo de leitura a partir
dos dados atuais dos módulos donos.
