# Instruções para agentes de IA

Este arquivo é a fonte principal de contexto para qualquer IA que ajude a programar o LoadX.

`CONTRIBUTING.md` é a porta de entrada para o fluxo de contribuição humano ou
assistido por IA. Este `AGENTS.md` continua sendo a fonte obrigatória de contexto
e restrições para agentes de IA.

## Antes de qualquer alteração

1. Leia o `README.md` da raiz.
2. Leia os documentos `docs/00` até `docs/05`.
3. Leia `docs/08-padroes-desenvolvimento.md`.
4. Leia `docs/09-guia-para-ia.md`.
5. Leia o `README.md` da pasta que será alterada.
6. Verifique ADRs relacionadas em `docs/decisions/`.
7. Verifique se a alteração pertence a uma ocorrência aprovada.

`CONFIRMADO`: para trabalho pós-v1.0.0, consulte a divisão da versão em
[docs/07-divisao-equipe.md](docs/07-divisao-equipe.md). O planejamento aprovado
da v1.1.0 fica em [docs/planejamento/v1.1.0/00-visao-geral.md](docs/planejamento/v1.1.0/00-visao-geral.md).
OC01–OC61 são histórico e não devem ser renumeradas nem ter seus números
reutilizados. OC62 é a primeira ocorrência nova pós-v1.0.0; a v1.1.0 usa
OC62–OC78. O planejamento não substitui os critérios de aceite das Issues nem
aprova automaticamente novos contratos ou regras.

`CONFIRMADO`: para planejamento de releases posteriores à v1.1.0, consulte [docs/planejamento/roadmap-versoes.md](docs/planejamento/roadmap-versoes.md). O roadmap define direção de produto, SemVer e gates, mas não substitui Issues, critérios de aceite ou ADRs. A v1.2.0 reserva OC79–OC84; identificadores posteriores somente são definidos no planejamento da respectiva release.

## Marcadores obrigatórios de incerteza

Use estes marcadores sempre que documentar ou reportar algo:

- `CONFIRMADO`: existe no código, documentação oficial, ADR ou documento-base aprovado.
- `RECOMENDAÇÃO`: padrão técnico proposto para manter consistência, ainda sem ADR própria.
- `SUPOSIÇÃO TÉCNICA`: inferência feita a partir da estrutura atual.
- `PENDENTE DE DEFINIÇÃO`: a equipe ainda precisa detalhar.
- `DECISÃO NECESSÁRIA`: exige escolha explícita da equipe antes de implementar.
- `RISCO IDENTIFICADO`: pode causar retrabalho, inconsistência ou falha operacional.

Não apresente suposições como decisões aprovadas.

## Escopo do MVP

Inclui caminhões, produtos, clientes, motoristas, pedidos, planejamento 3D, carregamento, entregas, ocorrências, relatórios e WhatsApp simulado ou controlado.

Não inclui paletes, GPS real, câmera, OpenCV, MDF-e, roteirização externa, previsão meteorológica, telemetria ou treinamento de modelo próprio.

## Convenções obrigatórias

- Dimensões internas e dos produtos são armazenadas em centímetros.
- Peso é armazenado em quilogramas.
- Coordenadas usam `x = largura`, `y = altura`, `z = comprimento`.
- A origem `(0, 0, 0)` fica no piso, no canto frontal esquerdo do baú.
- IDs são UUID, salvo decisão registrada em ADR.
- Datas e horários são armazenados em UTC.
- Nomes de código, tabelas, rotas e campos ficam em inglês.
- Textos de interface e documentação podem ficar em português.
- Endpoints públicos usam kebab-case no caminho e JSON em snake_case.

## Arquitetura

- Monólito modular.
- Rotas HTTP apenas validam entrada, chamam serviços e formatam respostas.
- Regras de negócio ficam em `service.py` ou `domain/`.
- Acesso ao banco fica em `repository.py`.
- Models SQLAlchemy ficam no módulo dono da tabela.
- Schemas Pydantic ficam em `schemas.py`.
- Integrações externas ficam atrás de interfaces/adapters em `app/integrations`.
- Módulos não acessam diretamente tabelas internas de outros módulos sem service público.

## Procedimento para novas funcionalidades

1. Confirme a ocorrência, objetivo e critérios de aceite.
2. Leia os contratos e regras relacionados em `docs`.
3. Use a menor mudança coerente com o módulo dono.
4. Crie somente arquivos necessários para a ocorrência atual.
5. Adicione ou atualize testes da regra de negócio ou do contrato alterado.
6. Atualize documentação quando mudar arquitetura, banco, regras, fluxos, API ou padrão.
7. Informe pendências quando algo depender de decisão da equipe.

## Banco e migrations

- A estrutura oficial do PostgreSQL vem de migrations Alembic.
- Não altere banco manualmente como solução definitiva.
- Não crie tabela, coluna, índice ou constraint fora de `docs/03-modelo-dados.md`.
- Tabelas usam plural em snake_case.
- Chaves primárias usam `id`.
- Chaves estrangeiras usam `<tabela_singular>_id`.
- Colunas de dimensão terminam em `_cm`.
- Colunas de peso terminam em `_kg`.
- Datas e horários terminam em `_at`.
- Dados de seed devem ser fictícios.

## Regras para geração de código

- Faça mudanças pequenas e focadas.
- Não invente campos, endpoints, estados, tecnologias ou regras de negócio.
- Não crie dependência externa sem justificar e atualizar os arquivos de dependências.
- Não grave segredos, tokens ou URLs privadas.
- Não use dados pessoais reais em seeds ou testes.
- Adicione ou atualize testes para toda regra de negócio.
- Nunca marque uma ocorrência como concluída sem teste mínimo.
- Não altere a estrutura principal do projeto sem aprovação.
- Não substitua padrões existentes por preferência pessoal.

## Otimização de carga

- A IA generativa não posiciona volumes diretamente.
- O otimizador deve ser determinístico, testável e reproduzível.
- Uma solução inválida nunca pode ser aceita para melhorar a porcentagem de ocupação.
- Colisão, limites, rotação, peso e apoio devem ser validados por código.
- O frontend apenas exibe coordenadas aprovadas pelo backend.

## O que não pode mudar sem aprovação

- Escopo do MVP.
- Convenções de unidade e coordenadas.
- Prefixo e contratos públicos da API.
- Tecnologia principal de backend, frontend ou banco.
- Estratégia de monólito modular.
- Modelo de dados aprovado.
- Regras críticas do otimizador.
- Integração real com provedor externo paga ou com credenciais.

## Contrato obrigatório de Pull Request

`CONFIRMADO`: todo Pull Request destinado a `desenvolvimento` deve estar
vinculado a exatamente uma Issue do mesmo repositório usando `Closes #NN`,
`Fixes #NN` ou `Resolves #NN`.

Para uma ocorrência `OCXX`:

- o título do PR começa com `[OCXX]`;
- o corpo contém `Identificador: OCXX`;
- o identificador precisa corresponder ao prefixo da Issue;
- a branch do PR deve ser exatamente a definida em `## Branch sugerida`;
- a Issue precisa estar aberta, atribuída ou possuir `## Responsável`;
- a Issue precisa pertencer ao Project `LoadX — Desenvolvimento`;
- a Issue precisa estar no milestone da versão que o bot acompanha.

Para trabalho que não pertence a uma OC:

- ainda é obrigatório vincular exatamente uma Issue;
- usar `Identificador: N/A`.

Nunca remova, contorne ou neutralize
`.github/workflows/validar-contrato-pr.yml`.
Se a validação falhar, corrija Issue, branch, título ou corpo do PR em vez de
tentar burlar o check.

Ao usar `gh pr create`, Codex, Claude ou qualquer outra automação, preserve
integralmente o contrato definido em `.github/pull_request_template.md`.

## Ao terminar uma tarefa

Informe:

1. arquivos alterados;
2. decisão tomada;
3. testes executados;
4. pendências ou riscos;
5. documentação atualizada.
