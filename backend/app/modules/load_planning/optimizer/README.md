# Otimizador

Implementa a heurística tridimensional do LoadX.

## Entrada mínima

- dimensões e peso máximo do caminhão;
- lista de volumes individuais;
- dimensões, peso, rotação, fragilidade, empilhamento e sequência de entrega.

## Saída mínima

- volumes posicionados com X, Y, Z e dimensões utilizadas;
- ordem de carregamento;
- volumes rejeitados e motivo;
- ocupação percentual;
- peso total;
- versão do algoritmo.

## Etapas previstas

1. expandir quantidades em volumes individuais;
2. ordenar volumes;
3. gerar rotações permitidas;
4. gerar pontos candidatos;
5. validar limites;
6. validar colisões;
7. validar apoio e empilhamento;
8. escolher posição;
9. calcular métricas.

## Restrições

O otimizador não acessa banco, HTTP, FastAPI ou provedor de IA. Ele recebe objetos simples e retorna resultado determinístico.

## OC11 - capacidade do caminhão

`CONFIRMADO`: o cálculo inicial de capacidade fica em `capacity.py`.

Entrada:

- `internal_width_cm`;
- `internal_height_cm`;
- `internal_length_cm`;
- `max_weight_kg`.

Saída:

- dimensões internas preservadas em centímetros;
- `internal_volume_cm3`;
- `max_weight_kg`.

Regras:

- Dimensões internas devem ser maiores que zero.
- Peso máximo deve ser maior que zero.
- O cálculo é determinístico e não acessa banco, HTTP ou IA.
