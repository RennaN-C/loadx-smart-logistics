# ADR-002: unidades e coordenadas

Status: aceita

## Decisão

- dimensões em centímetros;
- peso em quilogramas;
- X é largura;
- Y é altura;
- Z é comprimento;
- origem no piso, canto frontal esquerdo.

## Consequências

Backend, testes e frontend 3D devem usar a mesma convenção. Conversões visuais não podem alterar os valores persistidos.
