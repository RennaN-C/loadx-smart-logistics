# SonarCloud — triagem PR #388 (30/10/2026)

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
