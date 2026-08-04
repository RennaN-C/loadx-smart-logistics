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
- `CONFIRMADO`: OC14 gera rotações ortogonais permitidas, com códigos priorizados e simetrias deduplicadas.
- `CONFIRMADO`: OC15 gera pontos candidatos estáveis e seleciona por first-fit uma posição provisória, com limites validados antes de uma política física obrigatória.
- `CONFIRMADO`: OC16 rejeita candidatos com sobreposição positiva nos três eixos em relação a qualquer caixa já posicionada, permite contato e usa tolerância zero.
- `CONFIRMADO`: OC17 exige apoio integral pela união exata de múltiplos suportes e valida empilhamento e fragilidade por toda a cadeia de carga.
- `CONFIRMADO`: OC18 controla o peso incremental com `Decimal`, formaliza os sete motivos públicos e seleciona o motivo final pela precedência fixa da `ADR-011`.
- `CONFIRMADO`: OC19 calcula volume usado, peso colocado, ocupação com duas casas, contagens e `heuristic-v1` conforme a `ADR-012`.
- `CONFIRMADO`: OC20 ainda não foi implementada e, por isso, os validadores e as métricas permanecem isolados até a composição da engine.
- `CONFIRMADO`: persistência, service e API permanecem ausentes e pertencem à integração da OC20.

`RISCO IDENTIFICADO`: as regras isoladas atuais não representam um plano publicável. Nenhuma posição deve chegar ao frontend enquanto colisão, apoio, empilhamento, fragilidade, peso, motivo final e revalidação física não estiverem compostos pela engine.
