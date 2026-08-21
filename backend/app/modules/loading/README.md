# Carregamento

Checklist e estados do processo físico após aprovação do plano.

## Estado atual

`CONFIRMADO`: `reference_service.py` oferece a fronteira pública consumida pela
OC09. Até existir persistência real do carregamento, ela retorna `false` e
bloqueia de forma segura o início da viagem.

`PENDENTE DE DEFINIÇÃO`: models, migration, checklist, service e endpoints do
carregamento ainda precisam ser implementados pelo módulo dono.

## Estrutura sugerida

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.
