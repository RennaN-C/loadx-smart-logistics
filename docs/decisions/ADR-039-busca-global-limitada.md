# ADR-039: sugestões globais limitadas e autorização antes da consulta

Status: proposta para revisão na OC107 (#154).

`CONFIRMADO`: ADR-038 está reservada pela PR #211 (OC98), ainda não integrada
nesta base. Esta ADR não incorpora nem altera sua implementação.

## Contexto

A OC95 oferece consultas paginadas e whitelists por recurso. A busca do cabeçalho
precisa compor sugestões com limite independente por categoria, preservando a
minimização e autorização da ADR-017, sem criar um índice separado.

## Decisão implementada para revisão

- O agregador chama somente serviços públicos dos módulos autorizados ao perfil.
  Filtros, paginação, escaping e ordenação permanecem nos repositories da OC95.
- Cada categoria usa página 1, limite 1–10, created_at/id descendentes. O termo
  obrigatório tem 2–120 caracteres após trim. Não há nova semântica de acentos.
- `results` é uma projeção de sugestões (`category/id/title/href`), sem totais
  globais ou categorias vazias/restritas. Este envelope difere da coleção paginada
  da ADR-017 porque não oferece paginação transversal nem afirma exaustividade;
  as listagens de domínio mantêm seus envelopes e permitem a consulta completa.
- Cadastros ativos; pedidos/viagens históricos preservados. Nem arquivamento nem
  busca alteram disponibilidade ou regras operacionais.
- CHECKER não consulta nomes/clientes/motoristas/viagens. DRIVER utiliza a mesma
  validação de vínculo/atividade do TripService e filtro SQL por driver_id.
- Viagens pesquisam somente seu UUID. Nenhum documento, e-mail, telefone, CNH,
  evidência, usuário administrativo, plano ou carregamento é incluído implicitamente.
- O frontend aplica debounce/cancelamento, mas nunca é a fonte da autorização.
  Resultados apontam para detalhes ou listas filtradas reais; sem novas centrais.

## Consequências e limites

`CONFIRMADO`: não há migration, dependência, mudança de autenticação ou índice
novo. Reuso das páginas inclui COUNT e carregamento limitado de itens de pedido;
a quantidade de consultas independe do número de resultados dentro do limite.

`RISCO IDENTIFICADO`: ILIKE parcial permanece sujeito ao custo de varredura da
OC95. Limite de saída não garante latência em qualquer volume de dados. Índices
futuros exigem medição com dados representativos e revisão própria.

`PENDENTE DE DEFINIÇÃO`: incorporação desta proposta após revisão humana da PR;
PR #211/OC98 e #214/aparência permanecem isoladas enquanto abertas.
