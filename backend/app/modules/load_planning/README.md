# Planejamento de carga

Núcleo do sistema: expansão de volumes, rotações, pontos candidatos, colisões, peso, ocupação e persistência do plano.

## Estrutura sugerida

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Estado incremental

- `CONFIRMADO`: OC11 calcula e valida a capacidade do caminhão no núcleo puro.
- `CONFIRMADO`: OC12 calcula o volume individual, expande quantidades com `volume_index` iniciado em `1` e não cria tabela separada `volumes`.
- `CONFIRMADO`: OC13 ordena volumes por uma chave total determinística e independente da ordem de entrada.
- `CONFIRMADO`: existem primitivas isoladas para limites/classificação geométrica da OC16 e controle de peso da OC18.
- `PENDENTE DE DEFINIÇÃO`: OC14–OC17, OC19 e OC20 ainda dependem das regras totais registradas em `docs/11-riscos-pendencias.md` antes de formar uma engine.
- `DECISÃO NECESSÁRIA`: persistência, service e API não podem ser iniciados antes da engine fisicamente completa e dos contratos de estado/transação.

`RISCO IDENTIFICADO`: as primitivas atuais não representam um plano publicável. Nenhuma posição deve chegar ao frontend enquanto rotação, apoio, empilhamento, fragilidade, peso, colisão e revalidação final não estiverem integrados.
