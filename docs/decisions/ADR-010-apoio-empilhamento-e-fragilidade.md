# ADR-010: apoio integral, empilhamento e fragilidade

Status: aceita

## Contexto

A OC17 precisa decidir se uma configuração de volumes possui apoio estrutural válido sem antecipar a engine, o catálogo de rejeições, a persistência ou a API HTTP. A decisão deve cobrir piso, múltiplos suportes, transmissão de carga, empilhamento e fragilidade de forma exata e determinística.

## Decisão

- Um volume com a base no piso, em `y = 0`, é considerado integralmente apoiado e não possui suportes diretos.
- Para um volume acima do piso, outro volume é suporte direto somente quando o topo do suporte coincide exatamente com a base do volume apoiado e existe sobreposição com extensão estritamente positiva nos eixos `x` e `z`.
- A área apoiada é a união geométrica exata dos retângulos de contato em `x/z` de todos os suportes diretos. Regiões sobrepostas são contadas uma única vez.
- A base deve estar 100% coberta pela união dos suportes. Não há tolerância, arredondamento nem percentual de apoio parcial aceito.
- Cada aresta de apoio transmite carga positiva. A transmissão percorre todos os ramos até todos os ancestrais da configuração, sem ignorar caminhos por divisão de carga ou por limite mínimo.
- Todo suporte direto deve possuir `stackable = true`.
- Nenhum suporte direto ou ancestral que receba carga positiva pode possuir `fragile = true`.
- As flags do próprio volume apoiado não impedem sua colocação no topo: um candidato `fragile` ou `stackable = false` é válido quando nenhum volume acima transmite carga para ele.
- Não existe conceito ou limite de volume "pesado" para fragilidade; todo peso válido é positivo e, portanto, toda carga transmitida é positiva.
- `support.py` expõe a API pura `SupportAssessment`, `analyze_support_configuration`, `is_support_configuration_valid` e `is_candidate_support_valid`.
- A OC17 não cria engine, código público de rejeição, API HTTP ou persistência.

## Consequências

- Vários volumes podem sustentar conjuntamente uma base, desde que a união exata dos contatos cubra toda a área.
- Contatos apenas por aresta ou vértice em `x/z` não contribuem para a área apoiada.
- Um volume frágil em qualquer ramo ancestral invalida a configuração quando recebe carga positiva, ainda que não seja suporte direto do volume analisado.
- Um volume não empilhável só invalida a configuração quando atua como suporte direto de outro volume.
- As avaliações permanecem determinísticas, independentes da ordem de entrada e isoladas das camadas de aplicação.
- Alterar a cobertura integral, a propagação por todos os ramos ou a semântica de fragilidade exigirá nova `algorithm_version` quando a engine estiver integrada.
