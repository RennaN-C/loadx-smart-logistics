# Fleet

Serviço interno responsável por consolidar a disponibilidade operacional de
caminhões e motoristas.

## OC67 — disponibilidade da frota

A disponibilidade não é persistida. Ela é calculada a partir do estado atual
das entidades e das regras de conflito pertencentes aos módulos de caminhões e
motoristas.

### Caminhão

Um caminhão está disponível quando:

- existe;
- `active` é `true`;
- `TruckService.has_operation_conflict(...)` retorna `false`.

A regra de conflito pertence à OC64 e não deve ser reproduzida neste módulo.

### Motorista

Um motorista está disponível quando:

- existe;
- `active` é `true`;
- `DriverService.has_operation_conflict(...)` retorna `false`.

A regra de conflito pertence à OC65 e não deve ser reproduzida neste módulo.

### Operação

Uma combinação caminhão/motorista está disponível somente quando ambos estão
disponíveis individualmente.

### Fronteira pública

`FleetAvailabilityService` expõe:

- `get_truck_availability(truck_id)`;
- `get_driver_availability(driver_id)`;
- `get_operation_availability(truck_id, driver_id)`.

Cada consulta individual informa:

- identificador da entidade;
- estado cadastral `active`;
- existência de conflito operacional;
- disponibilidade calculada.

A consulta combinada contém os resultados do caminhão e do motorista e informa
se a operação está disponível.

### Entidades inexistentes

Caminhão ou motorista inexistente não é tratado simplesmente como
"indisponível".

Os erros já pertencentes aos módulos donos são preservados:

- `TruckNotFoundError`;
- `DriverNotFoundError`.

Isso permite que consumidores futuros decidam como traduzir a falha para seus
respectivos contratos HTTP.

## Restrições arquiteturais

Este módulo:

- não consulta diretamente tabelas de carregamento, viagens ou planejamento;
- não reimplementa as regras de OC64 ou OC65;
- não persiste disponibilidade;
- não cria novos estados operacionais;
- não possui endpoint próprio na OC67;
- não possui repository próprio porque não realiza persistência.

A fronteira é destinada ao consumo pelas OC68, OC69 e OC72.
