# ADR-008: posicionamento first-fit determinístico

Status: aceita

## Contexto

Depois de ordenar os volumes e gerar suas rotações, o otimizador precisa enumerar posições de forma finita, estável e reproduzível. A OC15 também precisa permanecer separada das políticas de colisão, apoio, empilhamento e fragilidade, que pertencem às ocorrências seguintes.

## Decisão

- Dimensões e coordenadas geométricas usam inteiros em centímetros.
- Os pontos candidatos incluem a origem `(0, 0, 0)` e, para cada caixa já posicionada em `(x, y, z)` com dimensões usadas `(w, h, l)`, as origens das três faces positivas: `(x + w, y, z)`, `(x, y + h, z)` e `(x, y, z + l)`.
- Coordenadas candidatas idênticas são deduplicadas por igualdade exata.
- Cada combinação de ponto e rotação é percorrida pela chave lexicográfica `(y, z, x, rotation_rank)`. `rotation_rank` segue a prioridade da `ADR-007`.
- A busca usa first-fit: retorna a primeira combinação que cabe nos limites internos e é aceita por uma política física fornecida explicitamente pelo chamador.
- A validação de limites sempre ocorre antes da política física.
- A política física é obrigatória e não possui comportamento permissivo padrão.
- Quando nenhuma rotação permitida cabe nas dimensões internas nem na origem, o motivo é `TRUCK_DIMENSIONS_EXCEEDED`.
- Quando existe rotação dimensionalmente viável, mas nenhuma combinação é aceita e nenhum motivo físico mais específico é produzido pela engine futura, o motivo de fallback é `NO_VALID_POSITION`.

## Consequências

- O mesmo volume, os mesmos pontos e a mesma política física produzem o mesmo candidato.
- O resultado da OC15 é um candidato provisório, não um plano fisicamente publicável.
- A OC15 não decide colisão, contato, apoio, empilhamento ou fragilidade. As OC16 e OC17 devem fornecer essas validações sem alterar a ordem de varredura aprovada.
- Uma posição só poderá ser persistida ou exposta pela API depois da integração e da revalidação de todas as regras físicas.
- Alterar a geração dos pontos, a chave de varredura ou a política first-fit exige nova `algorithm_version` quando a engine estiver integrada.
