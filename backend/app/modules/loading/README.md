# Carregamento

Checklist e estados do processo físico após aprovação do plano.

## Estado atual

`CONFIRMADO`: o módulo persiste uma sessão por plano aprovado e um item de
checklist para cada volume posicionado. O fluxo permitido é `PENDING ->
IN_PROGRESS -> FINISHED`; cada item avança de `PENDING` para `CHECKED` somente
durante `IN_PROGRESS`.

`CONFIRMADO`: a finalização exige todos os itens `CHECKED`. A fronteira pública
de `reference_service.py` libera `Trip SCHEDULED -> IN_ROUTE` somente quando a
sessão `FINISHED` pertence ao mesmo `load_plan_id`; sessão ausente, incompleta
ou de outro plano falha fechada.

## Estrutura

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.
