# Contribuindo com o LoadX

Obrigado por contribuir com o LoadX.

Este arquivo é a porta de entrada para contribuições humanas ou assistidas por IA. As regras técnicas e de domínio permanecem nas fontes canônicas do projeto.

## Antes de começar

Consulte, conforme a alteração:

1. `README.md` para visão geral;
2. `AGENTS.md` para regras obrigatórias de contexto e uso de IA;
3. `docs/08-padroes-desenvolvimento.md` para padrões técnicos;
4. `docs/09-guia-para-ia.md` quando houver assistência de IA;
5. a Issue responsável pela alteração;
6. o README do módulo ou feature afetada;
7. ADRs relacionadas em `docs/decisions/`.

Não recrie regras de negócio, contratos ou decisões arquiteturais neste arquivo.

## Fluxo de contribuição

Fluxo normal: Issue -> branch de trabalho -> implementação e testes -> Pull Request -> CI e revisão -> `desenvolvimento`.

Não faça push direto em `main` ou `desenvolvimento`.

## Issue

Toda alteração deve estar vinculada a uma Issue do repositório.

Para ocorrências funcionais, use o identificador `OCXX` definido no planejamento da versão. Para manutenção, documentação ou infraestrutura fora de OC, a Issue continua obrigatória e o Pull Request usa `Identificador: N/A`.

Não crie novas OCs nem reutilize identificadores sem planejamento aprovado.

## Branch

Para OCs, use exatamente a branch definida em `Branch sugerida` na Issue. Para trabalhos fora de OC, use nome curto, descritivo, em minúsculas e sem acentos.

## Commits

O projeto utiliza Conventional Commits com descrição em português.

## Implementação

Antes de alterar código, identifique o módulo dono, confirme os critérios de aceite, preserve contratos públicos, não invente regras, mantenha testes e atualize documentação quando necessário.

Os padrões detalhados permanecem em `docs/08-padroes-desenvolvimento.md`.

## Uso de IA

Contribuições assistidas por ChatGPT, Codex, Copilot, Claude ou outra IA são permitidas. A IA deve seguir integralmente `AGENTS.md` e `docs/09-guia-para-ia.md`.

## Pull Request

Todo Pull Request destinado a `desenvolvimento` deve fechar exatamente uma Issue usando `Closes`, `Fixes` ou `Resolves`.

Também deve possuir `Identificador: OCXX` para ocorrências ou `Identificador: N/A` para trabalhos fora de OC.

Nunca contorne `.github/workflows/validar-contrato-pr.yml`.

## Validação

Execute os checks aplicáveis antes de abrir o Pull Request. A CI é a validação final obrigatória.

## Segurança

Não publique senhas, tokens, chaves, credenciais, URLs privadas, dados pessoais reais ou provas de conceito contendo material sensível.

Vulnerabilidades devem seguir `SECURITY.md`.

## Decisões pendentes

`LICENSE` e `CODEOWNERS` somente devem ser adicionados após decisão explícita da equipe.
