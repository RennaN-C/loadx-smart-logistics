# ADR-007: rotações ortogonais dos volumes

Status: aceita

## Contexto

O posicionamento precisa conhecer todas as orientações ortogonais permitidas de um volume, com códigos e prioridade estáveis. Dimensões simétricas não podem gerar tentativas duplicadas, e produtos com rotação bloqueada devem manter a orientação original.

## Decisão

- Os eixos originais são `X = width`, `Y = height` e `Z = length`, conforme `ADR-002`.
- Cada `rotation_code` informa, na ordem, qual eixo original ocupa os eixos usados `x`, `y` e `z`.
- A prioridade oficial é `XYZ`, `XZY`, `YXZ`, `YZX`, `ZXY`, `ZYX`.
- Os mapeamentos de dimensões são `XYZ = (W,H,L)`, `XZY = (W,L,H)`, `YXZ = (H,W,L)`, `YZX = (H,L,W)`, `ZXY = (L,W,H)` e `ZYX = (L,H,W)`.
- Quando `rotation_allowed = false`, somente `XYZ` é gerada.
- Orientações com as mesmas dimensões usadas são deduplicadas, preservando o primeiro código da prioridade oficial.

## Consequências

- Um volume com três dimensões distintas produz seis orientações.
- Um cubo produz apenas `XYZ`; dimensões parcialmente simétricas produzem apenas as orientações geometricamente distintas.
- O posicionador futuro deve percorrer as rotações nesta ordem quando todos os critérios de posição anteriores forem iguais.
- Persistência, API e visualização devem usar os mesmos códigos.
- Os códigos representam atribuição de dimensões aos eixos, não polaridade ou face voltada para uma direção.
- Mudar códigos, semântica ou prioridade exige nova `algorithm_version` quando a engine estiver integrada.
