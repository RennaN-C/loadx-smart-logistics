# Documentação do LoadX

A documentação está separada entre **uso e manutenção atual**, **decisões arquiteturais** e **histórico recuperável**. Comece pelo assunto, não pela ordem de criação dos arquivos.

## Guia rápido

| Preciso... | Abra |
| --- | --- |
| Entender o produto e executar localmente | [README](../README.md) e [guia de ambientes](13-guia-execucao-ambientes.md) |
| Entender componentes e regras | [Arquitetura](02-arquitetura.md), [dados](03-modelo-dados.md), [regras](04-regras-negocio.md), [fluxo](06-fluxo-operacional.md) |
| Consultar as rotas | [Contratos de API](05-contratos-api.md) |
| Fazer alterações no código | [Guia de manutenção manual](14-guia-manutencao.md), [CONTRIBUTING](../CONTRIBUTING.md), [AGENTS](../AGENTS.md), [padrões](08-padroes-desenvolvimento.md) |
| Entender decisões de design/segurança | [Registro de ADRs](decisions/README.md) |
| Ver o comportamento de uma versão | [Releases](releases/), [CHANGELOG](../CHANGELOG.md) e [roadmap](planejamento/roadmap-versoes.md) |
| Analisar qualidade e pendências | [Riscos](11-riscos-pendencias.md), [qualidade](qualidade/) e [histórico de QA](evidencias/README.md) |
| Preparar testes de usabilidade | [Roteiro de usabilidade](usabilidade/README.md) |

## Estrutura e responsabilidade

- `docs/decisions/`: contratos arquiteturais, inclusive propostas ainda **não implementadas**. Verifique o status de cada ADR.
- `docs/releases/`: documentação das releases e limitações comprovadas no respectivo commit.
- `docs/planejamento/`: roadmap atual mais planos históricos de versões anteriores; planejamento **não é funcionalidade entregue**.
- `docs/evidencias/` e `docs/validacoes/`: índices de registros históricos, não diretórios de saída de testes.
- `docs/usabilidade/`: planejamento metodológico e roteiros; estudos automatizados não equivalem a pesquisa com pessoas.
- `qa/browser/`: fonte de testes automatizados que continua versionada.

## Política de evidências

Capturas de QA, relatórios de execução e arquivos de comparação antigos foram retirados da árvore **atual** para não sobrecarregar clones e revisões de código. **Não foram apagados do histórico Git**: consulte os índices [Evidências](evidencias/README.md) e [Validações](validacoes/README.md), que apontam ao commit exato `8948cf2e649c`.

Para novas validações, priorize **artefatos temporários do GitHub Actions** ou anexos à PR/Issue, com informações privadas removidas, e escreva no corpo da PR a ferramenta, o commit, o resultado e as limitações. Casos que precisem de retenção permanente devem seguir a política de retenção do projeto, não voltar a adicionar centenas de imagens na pasta de código.

## Antes de afirmar que algo está pronto

Confira código e testes no SHA final, status das PRs, migrações, condições do ambiente e status da implantação. `main`, `desenvolvimento` e `pentest-lab` podem ter capacidades diferentes; não use capturas antigas para inferir comportamento atual.
