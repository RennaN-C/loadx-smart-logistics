# ADR-016: campos decimais como número JSON

Status: aceita

## Contexto

O backend preserva pesos e percentuais com `Decimal` e `Numeric`, mas a
serialização padrão os publica como strings. O frontend de caminhões e os
exemplos do contrato já trabalham com números. Aceitar simultaneamente número e
string mantém o OpenAPI ambíguo e permite coerções silenciosas no consumidor.

Os campos atuais têm no máximo 11 dígitos significativos e até 3 casas decimais,
dentro da precisão segura adotada para `Number` no frontend. A aritmética do
otimizador não pode migrar para ponto flutuante por causa desta decisão de borda.

## Decisão

- Campos `Decimal` públicos usam exclusivamente número JSON na entrada e na
  saída. String numérica e booleano são entradas inválidas.
- O OpenAPI desses campos declara `type: number`, sem alternativa `string`.
- O backend converte o token JSON para `Decimal` durante a validação e mantém
  `Decimal`/`Numeric` em services, domínio, otimizador e PostgreSQL.
- A conversão para número ocorre somente na serialização da resposta HTTP.
- `max_weight_kg` mantém 2 casas; pesos de produto, item e total mantêm 3;
  `occupancy_percent` mantém 2 e continua calculado com `ROUND_HALF_UP`.
- Zeros finais não têm significado no JSON. Por exemplo, `12.500` pode ser
  serializado como `12.5` sem alteração do valor.
- Todo novo campo decimal público deve declarar precisão e escala e possuir no
  máximo 15 dígitos significativos. Um requisito acima desse limite exige nova
  decisão antes de expor o campo.

## Consequências

- Backend, frontend, documentação e OpenAPI passam a possuir um único tipo de
  transporte.
- O frontend não precisa converter respostas com `Number(value)` nem sustentar
  uniões `number | string`.
- A precisão determinística das ADR-011 e ADR-012 permanece inalterada porque
  nenhum cálculo de domínio passa a usar `float`.
- Clientes que enviavam strings decimais recebem erro `422` e precisam enviar
  tokens JSON numéricos.
