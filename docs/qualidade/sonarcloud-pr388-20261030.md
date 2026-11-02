# SonarCloud — triagem PR #388 (30/10/2026)

## Diagnóstico da main — 02/11/2026 — Issue #389

`CONFIRMADO`: após `git fetch origin --prune --tags`, a `main` permanece no
merge `f86f0ea367168e1a045a140fd2edf9f216560319`. A consulta das tags remotas e
das Releases públicas não encontrou `v1.3.0`; a última publicada é `v1.2.0`.

`CONFIRMADO`: a API `project_analyses/search` associa esse SHA à análise
`5055c96d-4cf0-48cb-832f-01197f70d812` (01/11/2026, 03:05:02 UTC).
O check [SonarCloud desse SHA](https://github.com/RennaN-C/loadx-smart-logistics/runs/124735307235)
está `completed/failure`: Security Rating C em código novo, exigido A.
`qualitygates/project_status` retorna `ERROR`, `new_security_rating=3`,
limite `1`; as outras quatro condições retornam `OK`.

`CONFIRMADO`: a consulta `issues/search` com `types=VULNERABILITY` e
`inNewCodePeriod=true` retornou exatamente um apontamento:

| Campo | Evidência |
| --- | --- |
| Issue Sonar | `AaEPWZ7BzQwPPfnD0zQH`, aberta |
| Regra | `githubactions:S8541` |
| Severidade | `MAJOR`; impacto `SECURITY/MEDIUM` |
| Local | `.github/workflows/ci.yml:61` |
| Descrição | Ausência de `--only-binary :all:` permite execução de scripts de instalação/build de distribuições fonte |

`CONFIRMADO`: o comando já exige hashes, mas permite sdists. É uma lacuna de
proteção da cadeia de dependências da CI, sem evidência de comprometimento ou
de falha em autenticação, MFA, RBAC ou lógica logística. A correção acrescenta
`--only-binary=:all:` e conserva lock, hashes e demais checks. A instalação
falha se não houver wheel compatível; não há fallback para compilação de fonte.

`CONFIRMADO`: o período de código novo da main é `previous_version`, com
baseline de 28/07/2026. O apontamento foi criado em 02/09/2026 e continua aberto.
A aprovação da PR #388 não comprova aprovação desse período da main.

`CONFIRMADO`: nos [logs de publicação](https://github.com/RennaN-C/loadx-smart-logistics/actions/runs/41267708462/job/124735823723),
o job falhou ao exigir Sonar aprovado para esse SHA. Checkout, validação de
versão/notas e criação de tag/release foram pulados. Backend, Frontend e Segurança
do backend passaram nessa execução. Nenhum outro bloqueio foi observado antes
dessa interrupção; as etapas posteriores ainda precisam executar após o gate.

`CONFIRMADO`: três regressões offline exercitam o comando real da CI com
artefatos fictícios: wheel com hash aprovado instala; hash divergente falha;
sdist com hash aprovado é recusada antes do hook de build. Remover a restrição
de binários faz a regressão da sdist falhar, comprovando sua sensibilidade.

`CONFIRMADO`: validação local em Windows/Python 3.12: Ruff check aprovado,
595 arquivos no format check e três regressões aprovadas. Download dos artefatos
do lock com hashes e somente wheels para CPython 3.12/manylinux aprovado
(`pip download --no-deps`, sem avaliar dependências transitivas pelo host Windows).
O YAML também foi carregado com `js-yaml`; o argumento `:all:` está entre aspas
para preservar a sintaxe do escalar YAML.

`CONFIRMADO`: frontend local: ESLint sem erros (dois warnings), 1.189 testes
aprovados, TypeScript/build e orçamento de bundle aprovados. `npm audit
--audit-level=high` terminou com exit code 0, mas registrou 14 vulnerabilidades
moderadas; isso não equivale a auditoria sem alertas. Node local 22.16.0 está
abaixo do intervalo do projeto; a CI usa a versão de `.nvmrc`.

`CONFIRMADO`: a suíte backend unitária/health local ampliada teve 1.707 aprovados,
seis falhas e dois erros. Cinco falhas envolvem storage com permissões POSIX;
outra é a ausência de APP_STOPPED no teste de encerramento do Uvicorn. Os dois
erros são do parâmetro extenso de Groq excedendo o limite de 32.767 caracteres
de variável de ambiente no Windows. Esses arquivos não foram alterados.
O lock Linux não instala integralmente no Windows (`uvloop`; dependência
`tzdata` específica do Windows ausente no lock Linux). Para os ensaios locais,
usou-se ambiente isolado, omitindo somente uvloop e a resolução transitiva,
sem alterar o lock. Docker estava indisponível; integração PostgreSQL e Trivy
devem ser comprovados na CI oficial. Não se declara suíte backend local verde.

`PENDENTE DE DEFINIÇÃO`: a aprovação Sonar da correção deve ser conferida na PR
e novamente no SHA da main após o merge normal. Não houve alteração do Quality
Gate, baseline, classificação do apontamento, lógica de publicação ou proteções.
Cobertura importada continua acompanhada separadamente pela Issue #268.

## Evidência verificável

- [Comentário do SonarCloud](https://github.com/RennaN-C/loadx-smart-logistics/pull/388#issuecomment-6530205880): **Quality Gate Passed**, **118 novos apontamentos**, **0 hotspots de segurança**, **0,0% coverage on new code** e **0,0% duplication on new code** no commit `8ef79ef5`.
- [CI dessa revisão](https://github.com/RennaN-C/loadx-smart-logistics/actions/runs/41104738972): Backend, Frontend e Segurança com sucesso; cobertura local não significa cobertura importada no Sonar (#268).
- Na verificação de 30/10/2026, o SonarCloud da `main` anterior (`0e5bd7ef`) constava em **failure**. O novo gate de publicação não reutiliza esse check: exige `success` do SHA após merge.

## Classificação

**118 issues novos não equivalem a 118 vulnerabilidades.** Em 30/10 foi fornecida a lista textual completa dos 118 apontamentos: **23 High, 88 Medium, 6 Low e 1 Info**. A grande maioria são alertas de manutenibilidade (complexidade cognitiva, testes pytest, CSS repetido, ternários, acessibilidade e chaves React). Foram identificados arquivos/linhas e categorias, mas os identificadores/regras de cada issue ainda exigem reanálise do SonarCloud para confirmar fechamento. A classificação por classe de severidade está documentada; a validação individual de correção permanece **PENDENTE**. Zero hotspots não garante ausência de alertas de segurança; Quality Gate aprovado não equivale a ausência de dívida técnica.

[Consultar issues da PR](https://sonarcloud.io/project/issues?id=RennaN-C_loadx-smart-logistics&pullRequest=388&issueStatuses=OPEN,CONFIRMED&sinceLeakPeriod=true).

## Critérios de encerramento

1. Exportar lista dos issues do HEAD com regra, severidade, tipo, arquivo, linha e descrição; recontar após nova CI.
2. Priorizar BLOCKER/HIGH de segurança e confiabilidade; avaliar Groq, autenticação, permissões, dados privados, locks e falhas de integração.
3. Classificar MEDIUM/LOW/INFO por impacto; corrigir ou criar Issue específica / aceitação justificada, nunca ignorar em lote.
4. Corrigir a importação de cobertura CI → SonarCloud ([#268](https://github.com/RennaN-C/loadx-smart-logistics/issues/268)).
5. Registrar severidades e evidências na auditoria incremental ([#256](https://github.com/RennaN-C/loadx-smart-logistics/issues/256)). Validar novamente SonarCloud no HEAD da PR e SHA final da `main`.

**Limite desta revisão:** o texto dos 118 apontamentos foi fornecido, mas não os registros detalhados com regras/keys e status após correção. O novo workflow bloqueia a publicação automática se o Sonar da main não concluir com `success`, mas isso não garante a eliminação de todas as issues.
